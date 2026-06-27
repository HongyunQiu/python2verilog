#!/usr/bin/env python3
"""FIR Filter - Cycle-Accurate Model

关键设计原则：
1. @combinational: 组合逻辑（映射到always @(*)）
2. @sequential: 时序逻辑（映射到always @(posedge clk)）
3. reg_前缀：寄存器变量
4. wire_前缀：组合逻辑中间值

两级抽象支持：
- Level 1 (Behavioral): Golden Model，用于算法验证和代码审查
- Level 2 (Structural): Cycle Model，用于硬件行为模拟和Verilog转换
"""

from typing import List, Optional
import functools


def combinational(func):
    """装饰器：标记组合逻辑函数"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._logic_type = "combinational"
    return wrapper


def sequential(func):
    """装饰器：标记时序逻辑函数"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._logic_type = "sequential"
    return wrapper


class FIRCycleModel:
    def __init__(self, num_taps, data_width=16, coeff_width=16, frac_bits=14):
        self.num_taps = num_taps
        self.data_width = data_width
        self.coeff_width = coeff_width
        self.frac_bits = frac_bits
        
        # 寄存器：延迟线存储num_taps-1个历史样本
        self.reg_delay_line = [0] * (num_taps - 1)
        self.reg_coefficients = [0] * num_taps
        self.reg_out = 0
        self.reg_valid_out = False
        
        # 组合逻辑中间值
        self.wire_acc = 0
        self.wire_out = 0
        self.wire_valid_out = False
        
        self.reset = True
        self.configured = False
        
    def configure(self, coefficients):
        assert len(coefficients) == self.num_taps
        self.reg_coefficients = coefficients[:]
        self.configured = True
        
    @combinational
    def compute(self, new_sample, valid_in=True):
        """
        组合逻辑：
        - reg_delay_line[0..num_taps-2]: 历史输入（寄存器）
        - new_sample: 当前输入（组合逻辑直通）
        
        effective_line = [历史样本...] + [新输入]
        """
        if self.reset:
            self.wire_acc = 0
            self.wire_out = 0
            self.wire_valid_out = False
            return None
        
        if not self.configured:
            self.wire_valid_out = False
            return None
        
        # 构建有效的延迟线
        effective_line = self.reg_delay_line + [new_sample]
        
        # MAC计算
        acc = 0
        for i in range(self.num_taps):
            product = effective_line[i] * self.reg_coefficients[i]
            acc += product
            
        self.wire_acc = acc
        result = acc >> self.frac_bits
        
        # 饱和截断
        max_val = 2**(self.data_width-1)
        min_val = -max_val
        self.wire_out = max(min_val, min(max_val - 1, result))
        self.wire_valid_out = valid_in
        return self.wire_out
        
    @sequential
    def clock(self):
        """
        时序逻辑：更新寄存器
        reg_delay_line移位，加入新样本
        """
        if self.reset:
            self.reg_delay_line = [0] * (self.num_taps - 1)
            self.reg_out = 0
            self.reg_valid_out = False
            return
            
        # 更新延迟线：移位并加入新样本
        if self.num_taps > 1:
            self.reg_delay_line = self.reg_delay_line[1:] + [self.new_sample]
        self.reg_out = self.wire_out
        self.reg_valid_out = self.wire_valid_out
        
    def step(self, new_sample, valid_in=True):
        self.new_sample = new_sample
        output = self.compute(new_sample, valid_in)
        self.clock()
        return output
        
    def run(self, input_samples):
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


def convert_coefficients_to_fixed_point(float_coefficients, coeff_width=16, frac_bits=14):
    fixed_coefficients = []
    scale = 2**frac_bits
    max_val = 2**(coeff_width-1)
    min_val = -max_val
    for coeff in float_coefficients:
        fixed = int(round(coeff * scale))
        fixed = max(min_val, min(max_val - 1, fixed))
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
