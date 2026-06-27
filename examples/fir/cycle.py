#!/usr/bin/env python3
"""FIR Filter - Cycle-Accurate Model (使用新框架)

关键设计原则：
1. @combinational: 组合逻辑（映射到always @(*)）
2. @sequential: 时序逻辑（映射到always @(posedge clk)）
3. reg_前缀：寄存器变量
4. wire_前缀：组合逻辑中间值
5. FixedPoint: 固定位宽整数，模拟Verilog截断行为

两级抽象支持：
- Level 1 (Behavioral): Golden Model，用于算法验证和代码审查
- Level 2 (Structural): Cycle Model，用于硬件行为模拟和Verilog转换
"""

import sys
import os
import functools
from typing import List, Optional

# 添加框架路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from framework import CycleModel, FixedPoint, fp, combinational, sequential


class FIRCycleModel(CycleModel):
    """FIR 滤波器 Cycle-Accurate 模型
    
    使用 FixedPoint 模拟硬件位宽行为，避免 Python 任意精度整数
    与 Verilog 固定位宽之间的语义鸿沟。
    """
    
    def __init__(self, num_taps: int, data_width: int = 16, coeff_width: int = 16, frac_bits: int = 14):
        super().__init__()
        self.num_taps = num_taps
        self.data_width = data_width
        self.coeff_width = coeff_width
        self.frac_bits = frac_bits
        
        # 寄存器：延迟线存储num_taps-1个历史样本
        self.reg_delay_line = [FixedPoint(0, width=data_width, signed=True)] * (num_taps - 1)
        self.reg_coefficients = [FixedPoint(0, width=coeff_width, signed=True)] * num_taps
        self.reg_out = FixedPoint(0, width=data_width, signed=True)
        self.reg_valid_out = False
        
        # 组合逻辑中间值
        self.wire_acc = FixedPoint(0, width=data_width + coeff_width + 2, signed=True)
        self.wire_out = FixedPoint(0, width=data_width, signed=True)
        self.wire_valid_out = False
        
        self.reset = True
        self.configured = False
        
        # 追踪信号
        self._track_signals()
        
    def configure(self, coefficients: List[int]):
        """配置滤波器系数"""
        assert len(coefficients) == self.num_taps
        self.reg_coefficients = [FixedPoint(c, width=self.coeff_width, signed=True) for c in coefficients]
        self.configured = True
        
    @combinational
    def compute(self, new_sample: int, valid_in: bool = True):
        """
        组合逻辑：
        - reg_delay_line[0..num_taps-2]: 历史输入（寄存器）
        - new_sample: 当前输入（组合逻辑直通）
        
        effective_line = [历史样本...] + [新输入]
        """
        if self.reset:
            self.wire_acc = FixedPoint(0, width=self.wire_acc.width, signed=True)
            self.wire_out = FixedPoint(0, width=self.data_width, signed=True)
            self.wire_valid_out = False
            return None
        
        if not self.configured:
            self.wire_valid_out = False
            return None
        
        # 将输入转换为 FixedPoint
        input_fp = FixedPoint(new_sample, width=self.data_width, signed=True)
        
        # 构建有效的延迟线
        effective_line = self.reg_delay_line + [input_fp]
        
        # MAC计算（使用 FixedPoint 模拟硬件位宽）
        acc = FixedPoint(0, width=self.data_width + self.coeff_width + 2, signed=True)
        for i in range(self.num_taps):
            product = effective_line[i] * self.reg_coefficients[i]
            acc = acc + product
            
        self.wire_acc = acc
        
        # 右移 frac_bits 位（模拟硬件移位）
        result = acc >> self.frac_bits
        
        # 饱和截断到 data_width
        max_val = 2**(self.data_width - 1) - 1
        min_val = -(2**(self.data_width - 1))
        saturated = max(min_val, min(max_val, result.value))
        
        self.wire_out = FixedPoint(saturated, width=self.data_width, signed=True)
        self.wire_valid_out = valid_in
        return self.wire_out.value
        
    @sequential
    def clock(self):
        """
        时序逻辑：更新寄存器
        reg_delay_line移位，加入新样本
        """
        if self.reset:
            self.reg_delay_line = [FixedPoint(0, width=self.data_width, signed=True)] * (self.num_taps - 1)
            self.reg_out = FixedPoint(0, width=self.data_width, signed=True)
            self.reg_valid_out = False
            return
            
        # 更新延迟线：移位并加入新样本
        if self.num_taps > 1:
            new_sample_fp = FixedPoint(self.new_sample, width=self.data_width, signed=True)
            self.reg_delay_line = self.reg_delay_line[1:] + [new_sample_fp]
        
        self.reg_out = self.wire_out
        self.reg_valid_out = self.wire_valid_out
        
    def step(self, new_sample: int, valid_in: bool = True):
        """执行一个时钟周期"""
        self.new_sample = new_sample
        output = self.compute(new_sample, valid_in)
        self.clock()
        return output
        
    def run(self, input_samples: List[int]) -> List[int]:
        """运行输入样本序列"""
        assert self.configured, "Must configure coefficients first!"
        output = []
        
        self.reset = True
        self.step(0, False)
        self.step(0, False)
        self.reset = False
        
        for sample in input_samples:
            out = self.step(sample, True)
            if out is not None:
                output.append(out)
        return output
    
    def get_resource_estimate(self) -> dict:
        """获取资源估算"""
        from framework.parallel import ResourceEstimator
        estimator = ResourceEstimator()
        return estimator.estimate(self)
    
    def check_dependencies(self) -> list:
        """检查组合逻辑依赖"""
        from framework.dependency_checker import DependencyChecker
        checker = DependencyChecker()
        return checker.check(self)


def convert_coefficients_to_fixed_point(float_coefficients, coeff_width=16, frac_bits=14):
    """将浮点系数转换为定点数"""
    fixed_coefficients = []
    scale = 2**frac_bits
    max_val = 2**(coeff_width-1) - 1
    min_val = -2**(coeff_width-1)
    for coeff in float_coefficients:
        fixed = int(round(coeff * scale))
        fixed = max(min_val, min(max_val, fixed))
        fixed_coefficients.append(fixed)
    return fixed_coefficients


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from golden import generate_test_vectors
    
    input_samples, float_coeffs, expected_output = generate_test_vectors(
        num_samples=10, num_taps=4, data_width=16)
    
    fir = FIRCycleModel(num_taps=4, data_width=16, frac_bits=14)
    fixed_coeffs = convert_coefficients_to_fixed_point(float_coeffs, coeff_width=16, frac_bits=14)
    fir.configure(fixed_coeffs)
    output = fir.run(input_samples)
    
    print("Golden:", expected_output)
    print("Cycle: ", output)
    
    max_error = max(abs(g-c) for g, c in zip(expected_output, output))
    print(f"Max error: {max_error}")
    
    if max_error <= 2:
        print("PASS")
    else:
        print("FAIL")
    
    # 展示新框架功能
    print("\n=== 新框架功能演示 ===")
    
    # 1. 信号追踪
    print(f"\n寄存器: {fir.get_reg_names()}")
    print(f"组合信号: {fir.get_wire_names()}")
    
    # 2. 资源估算
    resources = fir.get_resource_estimate()
    print(f"\n资源估算:")
    print(f"  FF: {resources['ff']}")
    print(f"  LUT: {resources['lut']}")
    
    # 3. 依赖检查
    errors = fir.check_dependencies()
    if errors:
        print(f"\n依赖检查错误: {errors}")
    else:
        print(f"\n依赖检查: 无环路")
    
    # 4. Verilog 头生成
    print(f"\nVerilog 头:")
    print(fir.generate_verilog_header("fir_filter"))
