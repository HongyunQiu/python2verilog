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
│   ├── fir/            # FIR滤波器示例
│   │   ├── golden.py   # Golden Model（算法层）
│   │   ├── cycle.py    # Cycle Model（行为层，使用新框架）
│   │   ├── template.v  # Verilog模板（实现层）
│   │   ├── tb_fir.v    # 测试平台（Testbench）
│   │   └── test.py     # 验证脚本
│   └── i2c_slave/      # I2C从机示例
│       ├── golden.py   # Golden Model（算法层）
│       ├── cycle.py    # Cycle Model（行为层）
│       ├── template.v  # Verilog模板（实现层）
│       ├── tb_i2c.v    # 测试平台（Testbench）
│       └── test.py     # 验证脚本
├── framework/          # 核心框架
│   ├── __init__.py     # 模块导出
│   ├── fixed_point.py  # FixedPoint：固定位宽整数类型
│   ├── base.py         # CycleModel基类 + 装饰器
│   ├── dependency_checker.py  # 组合逻辑环路检测
│   └── parallel.py     # 并行标注 + 资源估算
├── tests/              # 测试向量
├── docs/               # 文档
│   ├── phase1_summary.md
│   └── cycle_model_principle.html
└── artifacts/          # 临时仿真输出（不纳入版本控制）
```

## 核心框架模块

### FixedPoint - 固定位宽整数

解决 Python 任意精度整数与 Verilog 固定位宽之间的语义鸿沟。

```python
from framework import FixedPoint, fp

# 创建 8 位有符号数
a = fp(127, 8, signed=True)   # 范围 [-128, 127]
b = fp(-50, 8, signed=True)

# 加法自动扩展位宽防止溢出
c = a + b  # FixedPoint(77, width=9, signed=True)

# 乘法扩展位宽
d = a * b  # FixedPoint(-6350, width=16, signed=True)

# 强制截断
e = c.truncate(8, signed=True)

# 检查溢出
print(c.overflowed)  # False
```

### CycleModel - 硬件行为模拟基类

提供统一的 step()/compute()/clock() 接口，自动追踪信号。

```python
from framework import CycleModel, combinational, sequential

class MyModule(CycleModel):
    def __init__(self):
        super().__init__()
        self.reg_counter = fp(0, 8, signed=True)
        self.wire_next = fp(0, 9, signed=True)
    
    @combinational
    def compute(self, input_val):
        self.wire_next = self.reg_counter + input_val
        return self.wire_next.value
    
    @sequential
    def clock(self):
        self.reg_counter = self.wire_next.truncate(8, signed=True)
```

### DependencyChecker - 组合逻辑环路检测

静态分析 compute() 中的变量依赖，检测潜在环路。

```python
from framework import DependencyChecker

checker = DependencyChecker()
errors = checker.check(my_model)
if errors:
    for err in errors:
        print(f"环路: {err}")
else:
    print("✅ 无环路，组合逻辑安全")
```

### ResourceEstimator - FPGA 资源估算

粗略评估 LUT/FF/DSP 使用量。

```python
from framework import estimate_resources

resources = estimate_resources(my_model)
print(f"FF: {resources['ff']}")
print(f"LUT: {resources['lut']}")
print(f"DSP: {resources['dsp']}")
```

### @parallel - 并行度标注

标注可并行执行的计算，辅助资源估算。

```python
from framework import parallel

class MyModule(CycleModel):
    @parallel(channels=8, description="8通道并行处理")
    def compute_channels(self):
        for i in range(8):
            self.reg_out[i] = self.compute_channel(self.reg_in[i])
```

### @bitwidth - 位宽标注装饰器

为方法返回值添加位宽约束。

```python
from framework import bitwidth

class MyModule(CycleModel):
    @bitwidth(16, signed=True)
    def compute_accumulator(self):
        return self.reg_acc + self.reg_input  # 自动截断到16位
```

## 文件放置规范

### 目录职责

| 目录 | 职责 | 纳入版本控制 |
|------|------|-------------|
| `examples/` | 示例代码（Golden/Cycle/Verilog/Testbench） | ✅ 是 |
| `framework/` | 核心框架代码 | ✅ 是 |
| `tests/` | 测试向量 | ✅ 是 |
| `docs/` | 文档 | ✅ 是 |
| `artifacts/` | 临时仿真输出（编译产物、波形文件、日志） | ❌ 否 |

### 文件分类规则

**必须放入 `examples/<模块>/` 的文件：**
- `golden.py` - Golden Model（算法层）
- `cycle.py` - Cycle Model（行为层）
- `template.v` - Verilog模块源码
- `tb_*.v` - 测试平台（Testbench）
- `test.py` - 验证脚本

**必须放入 `artifacts/` 的文件（不纳入版本控制）：**
- `*.vvp` - 编译后的仿真二进制
- `*.vcd` - 波形文件
- `*.txt` - 仿真输出日志
- `*.hex` - 生成的数据文件
- 其他编译/仿真产物

### 命名规范

- 测试平台：`tb_<模块名>.v`（如 `tb_fir.v`, `tb_i2c.v`）
- Verilog模块：`template.v`（每个示例目录一个）
- Python文件：`golden.py`, `cycle.py`, `test.py`（固定命名）

## 快速开始

### 运行FIR示例验证

```bash
cd examples/fir
python test.py
```

### 运行I2C Slave示例验证

```bash
cd examples/i2c_slave
python test.py
```

### 验证结果

**FIR示例：**
```
Golden: [0, 1411, 5744, -3488, -14645, ...]
Cycle:  [0, 1411, 5744, -3489, -14645, ...]
Max error: 1 (允许≤2)
PASS: Golden vs Cycle 验证通过
```

**I2C Slave示例：**
```
PASS: Golden vs Cycle 验证通过
PASS: Cycle vs Verilog 逐位匹配验证通过
```

## 方法学价值

1. **降低AI认知负担**：AI只需理解compute()/clock()模式
2. **可审查性**：Python代码可被人类审查和理解
3. **渐进式验证**：每步有明确验证点
4. **可扩展性**：插件库可积累和复用
5. **位宽安全**：FixedPoint 模拟硬件截断，避免溢出隐患
6. **环路检测**：静态分析防止组合逻辑环路
7. **资源估算**：粗略评估 FPGA 资源使用量

## 现阶段成果

- ✅ Golden Model自验证通过
- ✅ Cycle Model实现时序/组合逻辑分离
- ✅ Golden vs Cycle验证通过（最大误差1）
- ✅ 方法学框架提取并持久化
- ✅ FixedPoint 固定位宽整数类型
- ✅ CycleModel 统一基类
- ✅ 组合逻辑环路检测器
- ✅ 并行度标注与资源估算

## 下一步方向

1. 完善验证链条：修复Verilog编译，完成Cycle vs Verilog逐位匹配
2. 扩展插件库：推广到其他模块（FFT、DMA、AXI等）
3. 自动化转换：开发Python→Verilog自动生成器
4. 方法学文档化：撰写完整指南
