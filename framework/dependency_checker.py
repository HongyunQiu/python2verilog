#!/usr/bin/env python3
"""Dependency Checker - 组合逻辑环路检测

通过静态分析 compute() 方法中的变量依赖关系，检测潜在的循环依赖。

用法：
    from framework.dependency_checker import DependencyChecker
    
    checker = DependencyChecker()
    
    # 分析一个 CycleModel 实例
    errors = checker.check(model)
    if errors:
        for err in errors:
            print(f"环路检测失败: {err}")
    else:
        print("无环路，安全")
    
    # 获取依赖图
    graph = checker.get_dependency_graph()
    print(f"依赖图: {graph}")
"""

import inspect
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict


class DependencyChecker:
    """组合逻辑依赖图分析器
    
    检测 compute() 方法中的变量读写依赖，发现循环依赖。
    """
    
    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._reads: Dict[str, Set[str]] = defaultdict(set)
        self._writes: Dict[str, Set[str]] = defaultdict(set)
        self._errors: List[str] = []
    
    def check(self, model: Any) -> List[str]:
        """检查模型是否有组合逻辑环路
        
        Args:
            model: CycleModel 实例
            
        Returns:
            错误列表，空列表表示无环路
        """
        self._graph.clear()
        self._reads.clear()
        self._writes.clear()
        self._errors.clear()
        
        # 获取 compute 方法
        compute_method = getattr(model, 'compute', None)
        if compute_method is None:
            self._errors.append("模型没有 compute() 方法")
            return self._errors
        
        # 获取源代码
        try:
            source = inspect.getsource(compute_method)
        except (OSError, TypeError):
            self._errors.append("无法获取 compute() 源代码")
            return self._errors
        
        # 分析源代码中的变量读写
        self._analyze_source(source, model)
        
        # 检测环路
        cycles = self._detect_cycles()
        
        for cycle in cycles:
            self._errors.append(f"检测到组合逻辑环路: {' -> '.join(cycle)}")
        
        return self._errors
    
    def _analyze_source(self, source: str, model: Any):
        """分析源代码中的变量读写依赖
        
        简化分析：
        - self.wire_x = ...  → 写入 wire_x
        - self.reg_x         → 读取 reg_x
        - self.wire_y        → 读取 wire_y
        """
        lines = source.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 跳过装饰器和 def 行
            if line.startswith('@') or line.startswith('def '):
                continue
            
            # 检测写入：self.wire_x = ... 或 self.reg_x = ...
            write_pattern = r'self\.(reg_\w+|wire_\w+)\s*='
            writes = re.findall(write_pattern, line)
            for var in writes:
                self._writes[var].add(line_num)
            
            # 检测读取：self.reg_x 或 self.wire_x（不在赋值左边）
            # 先移除赋值左边的变量
            cleaned_line = re.sub(r'self\.(reg_\w+|wire_\w+)\s*=[^=]', '', line)
            reads = re.findall(r'self\.(reg_\w+|wire_\w+)', cleaned_line)
            for var in reads:
                self._reads[var].add(line_num)
                # 建立依赖：写入的变量依赖于读取的变量
                for w_var in writes:
                    self._graph[w_var].add(var)
    
    def _detect_cycles(self) -> List[List[str]]:
        """检测依赖图中的环路（DFS）
        
        注意：排除自引用（如 acc = acc + x），这是合法的累加模式。
        真正的环路是 A 依赖 B 且 B 依赖 A（长度 >= 2 的环）。
        
        Returns:
            环路列表，每个环路是变量名列表
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self._graph.get(node, set()):
                # 跳过自引用（合法的累加模式）
                if neighbor == node:
                    continue
                
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # 找到环路（长度 >= 2）
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if len(cycle) >= 3:  # 至少两个不同变量 + 回到起点
                        cycles.append(cycle)
            
            path.pop()
            rec_stack.discard(node)
        
        # 从所有节点开始 DFS
        all_nodes = set(self._graph.keys())
        for targets in self._graph.values():
            all_nodes.update(targets)
        
        for node in all_nodes:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """获取依赖图
        
        Returns:
            依赖图：{写入变量: {读取变量1, 读取变量2, ...}}
        """
        return dict(self._graph)
    
    def get_reads(self) -> Dict[str, Set[int]]:
        """获取读取信息
        
        Returns:
            {变量名: {行号集合}}
        """
        return dict(self._reads)
    
    def get_writes(self) -> Dict[str, Set[int]]:
        """获取写入信息
        
        Returns:
            {变量名: {行号集合}}
        """
        return dict(self._writes)
    
    def print_dependency_report(self, model: Any):
        """打印依赖分析报告"""
        errors = self.check(model)
        
        print("=" * 60)
        print("组合逻辑依赖分析报告")
        print("=" * 60)
        
        print("\n写入变量:")
        for var, lines in sorted(self._writes.items()):
            print(f"  {var}: 行 {sorted(lines)}")
        
        print("\n读取变量:")
        for var, lines in sorted(self._reads.items()):
            print(f"  {var}: 行 {sorted(lines)}")
        
        print("\n依赖图:")
        for var, deps in sorted(self._graph.items()):
            print(f"  {var} 依赖于 {sorted(deps)}")
        
        if errors:
            print("\n❌ 环路检测失败:")
            for err in errors:
                print(f"  {err}")
        else:
            print("\n✅ 无环路，组合逻辑安全")
        
        print("=" * 60)


if __name__ == "__main__":
    # 测试环路检测
    print("=== 依赖检测器测试 ===")
    
    # 测试用例1：无环路
    class SafeModel:
        def compute(self):
            self.wire_a = self.reg_in + 1
            self.wire_b = self.wire_a * 2
            self.wire_out = self.wire_b - 1
    
    checker = DependencyChecker()
    errors = checker.check(SafeModel())
    print(f"安全模型: {len(errors)} 个错误")
    checker.print_dependency_report(SafeModel())
    
    # 测试用例2：有环路
    class CyclicModel:
        def compute(self):
            self.wire_a = self.wire_b  # wire_a 依赖 wire_b
            self.wire_b = self.wire_a  # wire_b 依赖 wire_a → 环路
    
    checker2 = DependencyChecker()
    errors2 = checker2.check(CyclicModel())
    print(f"\n环路模型: {len(errors2)} 个错误")
    checker2.print_dependency_report(CyclicModel())
    
    print("\n=== 测试完成 ===")
