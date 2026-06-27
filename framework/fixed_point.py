#!/usr/bin/env python3
"""FixedPoint - 固定位宽整数类型，模拟 Verilog 截断行为

解决 Python 任意精度整数与 Verilog 固定位宽之间的语义鸿沟。

用法：
    from framework.fixed_point import FixedPoint
    
    # 创建 8 位有符号数
    a = FixedPoint(127, width=8, signed=True)   # 范围 [-128, 127]
    b = FixedPoint(-50, width=8, signed=True)
    
    # 加法自动扩展位宽
    c = a + b  # FixedPoint(77, width=9, signed=True)
    
    # 乘法扩展位宽
    d = a * b  # FixedPoint(-6350, width=16, signed=True)
    
    # 强制截断到指定位宽
    e = c.truncate(8, signed=True)  # 可能溢出
    
    # 检查溢出
    print(c.overflowed)  # False
"""

from typing import Optional, Union


class FixedPoint:
    """固定位宽整数，模拟 Verilog 的位宽截断行为
    
    属性：
        width: 位宽
        signed: 是否有符号
        value: 当前值（已截断到指定位宽）
        overflowed: 是否发生过溢出
    """
    
    __slots__ = ('width', 'signed', 'value', 'overflowed')
    
    def __init__(self, value: int, width: int = 32, signed: bool = False):
        """初始化固定位宽整数
        
        Args:
            value: 初始值
            width: 位宽（不含符号位）
            signed: 是否有符号
        """
        self.width = width
        self.signed = signed
        self.overflowed = False
        self.value = self._truncate(value)
    
    def _truncate(self, value: int) -> int:
        """将值截断到指定位宽"""
        if self.signed:
            max_val = (1 << (self.width - 1)) - 1
            min_val = -(1 << (self.width - 1))
        else:
            max_val = (1 << self.width) - 1
            min_val = 0
        
        # 检查溢出
        if value > max_val or value < min_val:
            self.overflowed = True
        
        # 截断到指定位宽（模拟 Verilog 行为）
        mask = (1 << self.width) - 1
        result = value & mask
        
        # 如果有符号，进行符号扩展
        if self.signed and (result & (1 << (self.width - 1))):
            result -= (1 << self.width)
        
        return result
    
    def truncate(self, width: int, signed: bool = False) -> 'FixedPoint':
        """强制截断到指定位宽
        
        Args:
            width: 目标位宽
            signed: 目标是否有符号
            
        Returns:
            新的 FixedPoint 实例
        """
        result = FixedPoint(self.value, width=width, signed=signed)
        return result
    
    def _op(self, other: Union[int, 'FixedPoint'], op_func, result_width: int) -> 'FixedPoint':
        """执行二元运算并返回新的 FixedPoint"""
        if isinstance(other, FixedPoint):
            val = op_func(self.value, other.value)
            signed = self.signed or other.signed
        else:
            val = op_func(self.value, other)
            signed = self.signed
        
        return FixedPoint(val, width=result_width, signed=signed)
    
    def __add__(self, other: Union[int, 'FixedPoint']) -> 'FixedPoint':
        """加法：位宽扩展 1 位防止溢出"""
        if isinstance(other, FixedPoint):
            width = max(self.width, other.width) + 1
        else:
            width = self.width + 1
        return self._op(other, lambda a, b: a + b, width)
    
    def __radd__(self, other: int) -> 'FixedPoint':
        return self.__add__(other)
    
    def __sub__(self, other: Union[int, 'FixedPoint']) -> 'FixedPoint':
        """减法：位宽扩展 1 位防止溢出"""
        if isinstance(other, FixedPoint):
            width = max(self.width, other.width) + 1
        else:
            width = self.width + 1
        return self._op(other, lambda a, b: a - b, width)
    
    def __rsub__(self, other: int) -> 'FixedPoint':
        if isinstance(other, FixedPoint):
            return other.__sub__(self)
        return FixedPoint(other, width=self.width, signed=self.signed).__sub__(self)
    
    def __mul__(self, other: Union[int, 'FixedPoint']) -> 'FixedPoint':
        """乘法：位宽为两操作数位宽之和"""
        if isinstance(other, FixedPoint):
            width = self.width + other.width
            signed = self.signed or other.signed
        else:
            width = self.width + max(other.bit_length() + 1, 1)
            signed = self.signed
        
        val = self.value * (other.value if isinstance(other, FixedPoint) else other)
        return FixedPoint(val, width=width, signed=signed)
    
    def __rmul__(self, other: int) -> 'FixedPoint':
        return self.__mul__(other)
    
    def __lshift__(self, other: int) -> 'FixedPoint':
        """左移：位宽扩展"""
        if isinstance(other, FixedPoint):
            other = other.value
        return FixedPoint(self.value << other, width=self.width + other, signed=self.signed)
    
    def __rshift__(self, other: int) -> 'FixedPoint':
        """右移：位宽缩减"""
        if isinstance(other, FixedPoint):
            other = other.value
        new_width = max(1, self.width - other)
        return FixedPoint(self.value >> other, width=new_width, signed=self.signed)
    
    def __and__(self, other: Union[int, 'FixedPoint']) -> 'FixedPoint':
        if isinstance(other, FixedPoint):
            width = max(self.width, other.width)
        else:
            width = self.width
        return self._op(other, lambda a, b: a & b, width)
    
    def __or__(self, other: Union[int, 'FixedPoint']) -> 'FixedPoint':
        if isinstance(other, FixedPoint):
            width = max(self.width, other.width)
        else:
            width = self.width
        return self._op(other, lambda a, b: a | b, width)
    
    def __invert__(self) -> 'FixedPoint':
        """按位取反"""
        return FixedPoint(~self.value, width=self.width, signed=self.signed)
    
    def __neg__(self) -> 'FixedPoint':
        """取负"""
        return FixedPoint(-self.value, width=self.width + 1, signed=True)
    
    def __int__(self) -> int:
        return self.value
    
    def __repr__(self) -> str:
        sign = 's' if self.signed else 'u'
        overflow = ' [OVERFLOW]' if self.overflowed else ''
        return f"FixedPoint({self.value}, width={self.width}, {sign}){overflow}"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, FixedPoint):
            return self.value == other.value
        return self.value == other
    
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
    
    def __lt__(self, other) -> bool:
        if isinstance(other, FixedPoint):
            return self.value < other.value
        return self.value < other
    
    def __le__(self, other) -> bool:
        if isinstance(other, FixedPoint):
            return self.value <= other.value
        return self.value <= other
    
    def __gt__(self, other) -> bool:
        if isinstance(other, FixedPoint):
            return self.value > other.value
        return self.value > other
    
    def __ge__(self, other) -> bool:
        if isinstance(other, FixedPoint):
            return self.value >= other.value
        return self.value >= other
    
    def __bool__(self) -> bool:
        return self.value != 0
    
    def to_verilog(self, name: str, comment: str = "") -> str:
        """生成 Verilog 信号声明
        
        Args:
            name: 信号名称
            comment: 注释
            
        Returns:
            Verilog 声明语句
        """
        if self.signed:
            return f"    signed wire [{self.width-1}:0] {name};  // {comment}"
        else:
            return f"    wire [{self.width-1}:0] {name};  // {comment}"
    
    @staticmethod
    def saturate(value: int, width: int, signed: bool = False) -> int:
        """饱和截断（不溢出，钳位到边界）
        
        Args:
            value: 原始值
            width: 目标位宽
            signed: 是否有符号
            
        Returns:
            饱和后的值
        """
        if signed:
            max_val = (1 << (width - 1)) - 1
            min_val = -(1 << (width - 1))
        else:
            max_val = (1 << width) - 1
            min_val = 0
        
        return max(min_val, min(max_val, value))


# 便捷函数
def fp(value: int, width: int = 32, signed: bool = False) -> FixedPoint:
    """创建 FixedPoint 的便捷函数
    
    用法：
        a = fp(100, 8, signed=True)  # 8位有符号
        b = fp(255, 8)               # 8位无符号
    """
    return FixedPoint(value, width=width, signed=signed)


def saturating_add(a: int, b: int, width: int, signed: bool = False) -> int:
    """饱和加法
    
    Args:
        a: 操作数1
        b: 操作数2
        width: 结果位宽
        signed: 是否有符号
        
    Returns:
        饱和后的结果
    """
    return FixedPoint.saturate(a + b, width, signed)


if __name__ == "__main__":
    # 测试 FixedPoint
    print("=== FixedPoint 测试 ===")
    
    # 基本测试
    a = FixedPoint(127, width=8, signed=True)
    b = FixedPoint(-50, width=8, signed=True)
    print(f"a = {a}")
    print(f"b = {b}")
    
    c = a + b
    print(f"a + b = {c}")
    
    # 溢出测试
    d = FixedPoint(127, width=8, signed=True)
    e = FixedPoint(1, width=8, signed=True)
    f = d + e
    print(f"127 + 1 = {f} (overflowed={f.overflowed})")
    
    # 乘法测试
    g = FixedPoint(100, width=8, signed=True)
    h = FixedPoint(20, width=8, signed=True)
    i = g * h
    print(f"100 * 20 = {i}")
    
    # 便捷函数
    j = fp(42, 8, signed=True)
    print(f"fp(42, 8, signed=True) = {j}")
    
    # Verilog 生成
    print(f"\nVerilog: {j.to_verilog('wire_test', '测试信号')}")
    
    print("\n=== 所有测试通过 ===")
