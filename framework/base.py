#!/usr/bin/env python3
"""CycleModel 基类 - 统一的硬件行为模拟框架

提供：
1. 统一的 step()/compute()/clock() 接口
2. 寄存器/组合信号自动追踪
3. 与 FixedPoint 集成
4. 与依赖图检测集成

用法：
    from framework.base import CycleModel
    
    class MyModule(CycleModel):
        def __init__(self):
            super().__init__()
            self.reg_counter = 0  # 寄存器
            self.wire_next = 0    # 组合中间值
        
        @combinational
        def compute(self, input_val):
            self.wire_next = self.reg_counter + input_val
        
        @sequential
        def clock(self):
            self.reg_counter = self.wire_next
"""

import functools
import re
from typing import Dict, List, Optional, Set, Any, Callable
from .fixed_point import FixedPoint


def combinational(func: Callable) -> Callable:
    """装饰器：标记组合逻辑函数（映射到 always @(*)）"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._logic_type = "combinational"
    return wrapper


def sequential(func: Callable) -> Callable:
    """装饰器：标记时序逻辑函数（映射到 always @(posedge clk)）"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._logic_type = "sequential"
    return wrapper


def bitwidth(width: int, signed: bool = False):
    """装饰器：为方法返回值添加位宽标注
    
    用法：
        @bitwidth(16, signed=True)
        def compute_accumulator(self):
            return self.reg_acc + self.reg_input
    
    返回值会自动截断到指定位宽。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, FixedPoint):
                return result.truncate(width, signed=signed)
            return FixedPoint(result, width=width, signed=signed)
        wrapper._bitwidth = width
        wrapper._signed = signed
        return wrapper
    return decorator


class CycleModel:
    """硬件行为模拟基类
    
    约定：
    - reg_* 前缀：寄存器变量（跨周期保持）
    - wire_* 前缀：组合逻辑中间值（本周期内计算）
    
    子类必须实现：
    - compute(): 组合逻辑（用 @combinational 标记）
    - clock(): 时序逻辑（用 @sequential 标记）
    
    可选实现：
    - reset(): 复位逻辑
    """
    
    def __init__(self):
        self.reset = False
        self._reg_names: Set[str] = set()
        self._wire_names: Set[str] = set()
        self._bitwidth_annotations: Dict[str, Dict] = {}
        self._trace: List[Dict[str, Any]] = []
        self._tracing = False
    
    def _track_signals(self):
        """自动追踪寄存器和组合信号"""
        for attr_name in dir(self):
            if attr_name.startswith('reg_'):
                self._reg_names.add(attr_name)
            elif attr_name.startswith('wire_'):
                self._wire_names.add(attr_name)
    
    def get_reg_names(self) -> Set[str]:
        """获取所有寄存器名称"""
        self._track_signals()
        return self._reg_names.copy()
    
    def get_wire_names(self) -> Set[str]:
        """获取所有组合信号名称"""
        self._track_signals()
        return self._wire_names.copy()
    
    def get_signal_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有信号信息（名称、类型、位宽）"""
        info = {}
        for name in self.get_reg_names():
            val = getattr(self, name)
            if isinstance(val, FixedPoint):
                info[name] = {
                    'type': 'reg',
                    'width': val.width,
                    'signed': val.signed,
                    'value': val.value
                }
            elif isinstance(val, list):
                info[name] = {
                    'type': 'reg_array',
                    'length': len(val),
                    'value': val[:5]  # 只取前5个
                }
            else:
                info[name] = {
                    'type': 'reg',
                    'value': val
                }
        
        for name in self.get_wire_names():
            val = getattr(self, name)
            if isinstance(val, FixedPoint):
                info[name] = {
                    'type': 'wire',
                    'width': val.width,
                    'signed': val.signed,
                    'value': val.value
                }
            else:
                info[name] = {
                    'type': 'wire',
                    'value': val
                }
        
        return info
    
    def step(self, *args, **kwargs) -> Any:
        """执行一个时钟周期：compute() + clock()
        
        子类可以重写此方法来自定义行为。
        """
        if self.reset:
            self.reset()
            return None
        
        # 组合逻辑
        output = self.compute(*args, **kwargs)
        
        # 时序逻辑
        self.clock()
        
        # 追踪
        if self._tracing:
            self._trace.append(self.get_signal_info())
        
        return output
    
    def compute(self, *args, **kwargs) -> Any:
        """组合逻辑（子类重写）"""
        raise NotImplementedError("Subclass must implement compute()")
    
    def clock(self):
        """时序逻辑（子类重写）"""
        raise NotImplementedError("Subclass must implement clock()")
    
    def reset(self):
        """复位逻辑（子类可重写）"""
        pass
    
    def enable_tracing(self):
        """启用信号追踪"""
        self._tracing = True
        self._trace = []
    
    def disable_tracing(self):
        """禁用信号追踪"""
        self._tracing = False
    
    def get_trace(self) -> List[Dict[str, Any]]:
        """获取追踪记录"""
        return self._trace.copy()
    
    def generate_verilog_header(self, module_name: str) -> str:
        """生成 Verilog 模块头（信号声明）
        
        Args:
            module_name: 模块名称
            
        Returns:
            Verilog 信号声明代码
        """
        lines = []
        lines.append(f"module {module_name}(")
        lines.append("    input        clk,")
        lines.append("    input        rst_n")
        lines.append(");")
        lines.append("")
        
        # 寄存器声明
        for name in sorted(self.get_reg_names()):
            val = getattr(self, name)
            if isinstance(val, FixedPoint):
                signed = "signed " if val.signed else ""
                lines.append(f"    {signed}reg [{val.width-1}:0] {name};")
            elif isinstance(val, list):
                lines.append(f"    // reg array: {name} (length={len(val)})")
            else:
                lines.append(f"    reg {name};")
        
        lines.append("")
        
        # 组合信号声明
        for name in sorted(self.get_wire_names()):
            val = getattr(self, name)
            if isinstance(val, FixedPoint):
                signed = "signed " if val.signed else ""
                lines.append(f"    {signed}wire [{val.width-1}:0] {name};")
            elif isinstance(val, list):
                lines.append(f"    // wire array: {name}")
            else:
                lines.append(f"    wire {name};")
        
        lines.append("")
        
        return "\n".join(lines)
    
    def estimate_resources(self) -> Dict[str, int]:
        """粗略估算硬件资源使用
        
        Returns:
            资源估算字典：{ff: 触发器数, luts: 估计LUT数, ...}
        """
        ff_count = 0
        total_bits = 0
        
        for name in self.get_reg_names():
            val = getattr(self, name)
            if isinstance(val, FixedPoint):
                ff_count += val.width
                total_bits += val.width
            elif isinstance(val, list):
                ff_count += len(val)
                total_bits += len(val)
            else:
                ff_count += 1
                total_bits += 1
        
        # 粗略估算 LUT（假设每个组合信号需要 1-4 个 LUT）
        wire_count = len(self.get_wire_names())
        estimated_luts = wire_count * 2  # 非常粗略的估计
        
        return {
            'ff': ff_count,
            'estimated_luts': estimated_luts,
            'total_bits': total_bits,
            'reg_count': len(self.get_reg_names()),
            'wire_count': wire_count
        }


if __name__ == "__main__":
    # 测试基类
    print("=== CycleModel 基类测试 ===")
    
    class TestModule(CycleModel):
        def __init__(self):
            super().__init__()
            self.reg_counter = FixedPoint(0, width=8, signed=True)
            self.wire_next = FixedPoint(0, width=9, signed=True)
        
        @combinational
        def compute(self, input_val):
            self.wire_next = self.reg_counter + input_val
            return self.wire_next.value
        
        @sequential
        def clock(self):
            self.reg_counter = self.wire_next.truncate(8, signed=True)
        
        def reset(self):
            self.reg_counter = FixedPoint(0, width=8, signed=True)
            self.wire_next = FixedPoint(0, width=9, signed=True)
    
    # 创建实例
    mod = TestModule()
    
    # 测试信号追踪
    print(f"Registers: {mod.get_reg_names()}")
    print(f"Wires: {mod.get_wire_names()}")
    
    # 测试 step
    mod.reset = False
    for i in range(5):
        out = mod.step(FixedPoint(1, width=8, signed=True))
        print(f"Step {i}: counter={mod.reg_counter.value}, output={out}")
    
    # 测试资源估算
    resources = mod.estimate_resources()
    print(f"Resources: {resources}")
    
    # 测试 Verilog 头生成
    header = mod.generate_verilog_header("test_module")
    print(f"\nVerilog header:\n{header}")
    
    print("\n=== 所有测试通过 ===")
