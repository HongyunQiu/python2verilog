#!/usr/bin/env python3
"""Python2Verilog Framework - 核心框架模块

提供：
- FixedPoint: 固定位宽整数类型
- CycleModel: 硬件行为模拟基类
- DependencyChecker: 组合逻辑环路检测
- ResourceEstimator: FPGA 资源估算
- 装饰器: @combinational, @sequential, @parallel, @bitwidth

用法：
    from framework import (
        CycleModel, FixedPoint, fp,
        combinational, sequential, parallel, bitwidth,
        DependencyChecker, estimate_resources
    )
"""

from .fixed_point import FixedPoint, fp, saturating_add
from .base import (
    CycleModel,
    combinational,
    sequential,
    bitwidth,
)
from .dependency_checker import DependencyChecker
from .parallel import (
    parallel,
    ResourceEstimator,
    estimate_resources,
    print_resource_report,
)

__all__ = [
    # FixedPoint
    'FixedPoint',
    'fp',
    'saturating_add',
    # CycleModel
    'CycleModel',
    'combinational',
    'sequential',
    'bitwidth',
    # Dependency Checker
    'DependencyChecker',
    # Parallel & Resources
    'parallel',
    'ResourceEstimator',
    'estimate_resources',
    'print_resource_report',
]
