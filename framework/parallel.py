#!/usr/bin/env python3
"""Parallel Annotations - 并行度标注和资源估算

提供：
1. @parallel 装饰器：标注可并行执行的计算
2. 资源估算接口：粗略评估 LUT/FF/BRAM 使用量
3. 并行度分析报告

用法：
    from framework.parallel import parallel, estimate_resources
    
    class MyModule(CycleModel):
        @parallel(channels=8)
        def compute_channels(self):
            for i in range(8):
                self.reg_out[i] = self.compute_channel(self.reg_in[i])
    
    # 资源估算
    resources = estimate_resources(model)
    print(f"Estimated LUTs: {resources['lut']}")
    print(f"Estimated FFs: {resources['ff']}")
"""

import functools
import re
import inspect
from typing import Dict, List, Optional, Any, Callable, Set
from collections import defaultdict


def parallel(channels: int = 1, description: str = ""):
    """装饰器：标注可并行执行的计算
    
    Args:
        channels: 并行通道数
        description: 描述信息
    
    用法：
        @parallel(channels=8, description="8通道并行处理")
        def compute_channels(self):
            for i in range(8):
                self.reg_out[i] = self.compute_channel(self.reg_in[i])
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._parallel_channels = channels
        wrapper._parallel_description = description
        wrapper._is_parallel = True
        return wrapper
    return decorator


class ResourceEstimator:
    """资源估算器
    
    基于 Python 模型粗略估算 FPGA 资源使用量。
    
    估算规则（简化）：
    - 每个寄存器（reg_*）→ 1 FF（每 bit）
    - 每个加法器 → width LUTs
    - 每个乘法器 → width*width/2 LUTs（简化）
    - 每个比较器 → width/2 LUTs
    - 每个状态机 → states*log2(states) LUTs
    - 并行通道 → 资源乘以通道数
    """
    
    # 默认位宽假设
    DEFAULT_WIDTH = 16
    
    def __init__(self):
        self._resources: Dict[str, int] = {
            'ff': 0,        # Flip-Flops
            'lut': 0,       # Look-Up Tables
            'bram': 0,      # Block RAM
            'dsp': 0,       # DSP slices
            'lut_detail': {},  # LUT 使用明细
            'ff_detail': {},   # FF 使用明细
        }
    
    def estimate(self, model: Any) -> Dict[str, int]:
        """估算模型资源使用量
        
        Args:
            model: CycleModel 实例
            
        Returns:
            资源估算字典
        """
        self._resources = {
            'ff': 0,
            'lut': 0,
            'bram': 0,
            'dsp': 0,
            'lut_detail': {},
            'ff_detail': {},
        }
        
        # 估算寄存器（FF）
        self._estimate_regs(model)
        
        # 估算组合逻辑（LUT）
        self._estimate_combinational(model)
        
        # 估算并行通道
        self._estimate_parallel(model)
        
        return {
            'ff': self._resources['ff'],
            'lut': self._resources['lut'],
            'bram': self._resources['bram'],
            'dsp': self._resources['dsp'],
            'lut_detail': self._resources['lut_detail'],
            'ff_detail': self._resources['ff_detail'],
        }
    
    def _estimate_regs(self, model: Any):
        """估算寄存器资源（FF）"""
        for attr_name in dir(model):
            if attr_name.startswith('reg_'):
                val = getattr(model, attr_name)
                if isinstance(val, list):
                    # 数组寄存器
                    if len(val) > 0 and hasattr(val[0], 'width'):
                        width = val[0].width
                    elif len(val) > 0 and isinstance(val[0], int):
                        width = max(val[0].bit_length() + 1, 8)
                    else:
                        width = self.DEFAULT_WIDTH
                    ff_count = len(val) * width
                    self._resources['ff'] += ff_count
                    self._resources['ff_detail'][attr_name] = ff_count
                elif hasattr(val, 'width'):
                    # FixedPoint
                    width = val.width
                    self._resources['ff'] += width
                    self._resources['ff_detail'][attr_name] = width
                elif isinstance(val, int):
                    width = max(val.bit_length() + 1, 8)
                    self._resources['ff'] += width
                    self._resources['ff_detail'][attr_name] = width
                elif isinstance(val, bool):
                    self._resources['ff'] += 1
                    self._resources['ff_detail'][attr_name] = 1
    
    def _estimate_combinational(self, model: Any):
        """估算组合逻辑资源（LUT）"""
        compute_method = getattr(model, 'compute', None)
        if compute_method is None:
            return
        
        try:
            source = inspect.getsource(compute_method)
        except (OSError, TypeError):
            return
        
        # 检测运算操作
        additions = len(re.findall(r'\+', source))
        subtractions = len(re.findall(r'\-', source))
        multiplications = len(re.findall(r'\*', source))
        comparisons = len(re.findall(r'>=|<=|!=|==|>|<', source))
        bitwise_ops = len(re.findall(r'&|\||\^|~|<<|>>', source))
        
        width = self.DEFAULT_WIDTH
        
        # 加法器/减法器：约 width LUTs
        add_luts = (additions + subtractions) * width
        self._resources['lut'] += add_luts
        self._resources['lut_detail']['adders'] = add_luts
        
        # 乘法器：约 width*width/2 LUTs，或使用 DSP
        if multiplications > 0:
            mul_luts = multiplications * (width * width // 2)
            # 大乘法器使用 DSP
            if width >= 16:
                self._resources['dsp'] += multiplications
                self._resources['lut_detail']['multipliers'] = 0
            else:
                self._resources['lut'] += mul_luts
                self._resources['lut_detail']['multipliers'] = mul_luts
        
        # 比较器：约 width/2 LUTs
        comp_luts = comparisons * (width // 2)
        self._resources['lut'] += comp_luts
        self._resources['lut_detail']['comparators'] = comp_luts
        
        # 位运算：约 width LUTs
        bit_luts = bitwise_ops * width
        self._resources['lut'] += bit_luts
        self._resources['lut_detail']['bitwise'] = bit_luts
        
        # 状态机：检测 if/elif/else
        states = len(re.findall(r'\bif\b|\belif\b', source))
        if states > 0:
            sm_luts = max(states, 2) * 2  # 简化估算
            self._resources['lut'] += sm_luts
            self._resources['lut_detail']['state_machine'] = sm_luts
    
    def _estimate_parallel(self, model: Any):
        """估算并行通道资源"""
        for attr_name in dir(model):
            attr = getattr(model, attr_name)
            if callable(attr) and hasattr(attr, '_is_parallel'):
                channels = getattr(attr, '_parallel_channels', 1)
                if channels > 1:
                    # 并行通道会倍增资源
                    # 这里简化处理，实际需要根据具体逻辑估算
                    pass
    
    def print_report(self, resources: Dict[str, int]):
        """打印资源估算报告"""
        print("=" * 60)
        print("FPGA 资源估算报告（粗略）")
        print("=" * 60)
        
        print(f"\nFlip-Flops (FF):  {resources['ff']}")
        print(f"Look-Up Tables:   {resources['lut']}")
        print(f"Block RAM:        {resources['bram']}")
        print(f"DSP Slices:       {resources['dsp']}")
        
        if resources.get('ff_detail'):
            print("\nFF 明细:")
            for name, count in sorted(resources['ff_detail'].items()):
                print(f"  {name}: {count} FFs")
        
        if resources.get('lut_detail'):
            print("\nLUT 明细:")
            for name, count in sorted(resources['lut_detail'].items()):
                print(f"  {name}: {count} LUTs")
        
        print("\n注意：这是粗略估算，实际资源使用取决于综合工具和优化策略")
        print("=" * 60)


def estimate_resources(model: Any) -> Dict[str, int]:
    """便捷函数：估算模型资源
    
    Args:
        model: CycleModel 实例
        
    Returns:
        资源估算字典
    """
    estimator = ResourceEstimator()
    return estimator.estimate(model)


def print_resource_report(model: Any):
    """便捷函数：打印资源估算报告"""
    estimator = ResourceEstimator()
    resources = estimator.estimate(model)
    estimator.print_report(resources)


if __name__ == "__main__":
    # 测试资源估算
    print("=== 资源估算测试 ===")
    
    class TestModel:
        def __init__(self):
            self.reg_counter = 0
            self.reg_data = [0] * 8
            self.wire_out = 0
        
        def compute(self, input_val):
            self.wire_acc = self.reg_counter + input_val
            self.wire_product = self.wire_acc * 2
            self.wire_out = self.wire_product if self.wire_acc > 100 else 0
    
    model = TestModel()
    resources = estimate_resources(model)
    print_resource_report(model)
    
    print("\n=== 测试完成 ===")
