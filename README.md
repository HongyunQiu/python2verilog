# Python2Verilog Framework

基于AI辅助的FPGA开发方法学：三层建模 + 可验证转换

## 核心方法

### 三层建模

| 层级 | 职责 | 验证目标 |
|------|------|----------|
| **Golden Model** | 算法正确性（浮点Python） | 数学模型正确 |
| **Cycle Model** | 硬件行为模拟（时序/组合分离） | 与Golden行为一致 |
| **Verilog** | 可综合RTL实现 | 与Cycle逐位匹配 |

### 关键设计原则

1. **时序/组合逻辑显式分离**
   - `@combinational` → 映射为 `always @(*)`
   - `@sequential` → 映射为 `always @(posedge clk)`
   - `reg_`前缀=寄存器，`wire_`前缀=组合中间值

2. **两级抽象支持**
   - **Behavioral级**：Golden Model，用于算法验证和代码审查
   - **Structural级**：Cycle Model，用于硬件行为模拟

3. **可验证转换链条**
   - Golden → Cycle：允许量化误差（≤2 LSB）
   - Cycle → Verilog：要求逐位匹配（0误差）

## 项目结构

```
python2verilog/
├── README.md           # 本文件
├── examples/           # 示例代码
│   └── fir/            # FIR滤波器示例
│       ├── golden.py   # Golden Model（算法层）
│       ├── cycle.py    # Cycle Model（行为层）
│       ├── template.v  # Verilog模板（实现层）
│       └── test.py     # 验证脚本
├── framework/          # 核心框架
│   ├── base.py         # Cycle Model基类
│   ├── converter.py    # Python→Verilog转换器
│   └── verifier.py     # 验证对比工具
├── tests/              # 测试向量
└── artifacts/          # 仿真输出
```

## 快速开始

### 运行FIR示例验证

```bash
cd examples/fir
python test.py
```

### 验证结果

```
Golden: [0, 1411, 5744, -3488, -14645, ...]
Cycle:  [0, 1411, 5744, -3489, -14645, ...]
Max error: 1 (允许≤2)
PASS: Golden vs Cycle 验证通过
```

## 方法学价值

1. **降低AI认知负担**：AI只需理解compute()/clock()模式
2. **可审查性**：Python代码可被人类审查和理解
3. **渐进式验证**：每步有明确验证点
4. **可扩展性**：插件库可积累和复用

## 现阶段成果

- ✅ Golden Model自验证通过
- ✅ Cycle Model实现时序/组合逻辑分离
- ✅ Golden vs Cycle验证通过（最大误差1）
- ✅ 方法学框架提取并持久化

## 下一步方向

1. 完善验证链条：修复Verilog编译，完成Cycle vs Verilog逐位匹配
2. 扩展插件库：推广到其他模块（FFT、DMA、AXI等）
3. 自动化转换：开发Python→Verilog自动生成器
4. 方法学文档化：撰写完整指南
