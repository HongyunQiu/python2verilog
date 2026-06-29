# DDR Frame Buffer & Retransmit Manager - 项目状态报告

**日期**: 2026-06-29  
**项目路径**: `/home/bjtc/workspace/python2verilog/examples/ddr_frame_buffer/`

---

## 一、项目概述

基于 Altera Cyclone10 + DDR4 Memory Interface IP，实现图像帧的多页缓冲和重发管理器。采用 Python2Verilog 三层验证方法学（Golden Model → Cycle Model → RTL）。

### 核心参数（Full 配置）
| 参数 | 值 |
|------|-----|
| 帧分辨率 | 3840 × 2160 |
| 像素位深 | 16 bit |
| 帧数据大小 | 16,588,800 bytes |
| 帧总大小 | 16,588,816 bytes (~15.83 MB) |
| DDR4 容量 | 1 GB |
| 页大小 | 20 MB |
| 页数 | 50 |
| 包 Payload | 4096 bytes |
| 每帧包数 | 4050 |

### 三种配置
| 配置 | 分辨率 | 帧大小 | DDR | 页数 | 每帧包数 |
|------|--------|--------|-----|------|----------|
| **mini** | 32×32 | ~2KB | 256KB | 32 | 1 |
| **test** | 128×128 | ~32KB | 1MB | 16 | 9 |
| **full** | 3840×2160 | ~16MB | 1GB | 50 | 4050 |

---

## 二、已完成工作

### 2.1 Python 层（Golden Model）

| 文件 | 状态 | 说明 |
|------|------|------|
| `config.py` | ✅ 完成 | 三种配置（mini/test/full），FrameConfig 类动态计算派生参数 |
| `golden.py` | ✅ 完成 | 6 个核心模块，所有测试通过 |
| `cycle.py` | ⚠️ 部分完成 | 框架完整，但帧头检测存在 bug（见问题列表） |
| `rtl_params.py` | ✅ 完成 | RTL 参数生成脚本 |

**Golden Model 测试结果（test 配置）：**
- ✅ 帧数据完全匹配（32,784 bytes）
- ✅ 分包正确（9 包/帧）
- ✅ 重发机制正常（9 包排队）
- ✅ 多帧环形缓冲正常（5 帧写入 5 页）
- ✅ 页状态管理正确（FREE→WRITING→READY→READING）

### 2.2 RTL 层

| 文件 | 状态 | 说明 |
|------|------|------|
| `rtl/top.v` | ✅ 完成 | 完整参数化，支持三种配置 |
| `rtl/page_manager.v` | ⚠️ 部分完成 | 50 个状态寄存器硬编码（见问题列表） |
| `rtl/frame_writer.v` | ✅ 完成 | 参数化，帧头检测大端序 |
| `rtl/frame_reader.v` | ✅ 完成 | 参数化，帧尾检测大端序 |
| `rtl/output_arbiter.v` | ✅ 完成 | 参数化 |
| `rtl/command_interface.v` | ✅ 完成 | 参数化 |

**编译状态：**
- ✅ iverilog 编译通过，无警告
- ⚠️ 系统级仿真未完整验证（page_manager.v 测试 3/4 失败）

### 2.3 测试平台

| 文件 | 状态 | 说明 |
|------|------|------|
| `tb_system.v` | ✅ 存在 | 系统级仿真 |
| `tb_minimal.v` | ✅ 存在 | 最小化测试 |
| `tb_simple.v` | ✅ 存在 | 简化测试 |
| `tb_pm.v` | ✅ 存在 | Page Manager 测试 |
| `tb_ddr_frame_buffer.v` | ✅ 存在 | 完整测试 |
| `tb_fir.v` | ✅ 存在 | FIR 示例测试 |

---

## 三、已知问题

### 3.1 🔴 严重问题

#### P1: page_manager.v 状态寄存器硬编码
- **描述**: 内部 50 个页状态寄存器是硬编码的（`page_state_0` 到 `page_state_49`），不是真正参数化的
- **原因**: Icarus Verilog 不支持 generate 循环中的 unpacked arrays
- **影响**: 无法通过 NUM_PAGES 参数动态调整页数
- **解决方案**:
  1. **方案 A**: 使用 Quartus 的 generate 语法（需要 Quartus 编译）
  2. **方案 B**: 使用 memory array 替代独立寄存器（需要重构）
  3. **方案 C**: 保持硬编码，接受 NUM_PAGES 参数但内部固定 50 页

#### P2: Cycle Model 帧头检测 bug
- **描述**: cycle.py 中帧头检测使用移位寄存器，但帧头字节序处理与大端/小端有关
- **表现**: cycle.py 测试超时（可能陷入死循环）
- **原因**: 帧头 0x5A5A5A5AEE11DD22 在小端序下字节为 `\x22\xdd\x11\xee\x5a\x5a\x5a\x5a`，移位寄存器左移后值为 0x22DD11EE5A5A5A5A，需要正确匹配
- **状态**: 已定义 FRAME_HEADER_LE = 0x22DD11EE5A5A5A5A，但测试仍超时

### 3.2 🟡 中等问题

#### P3: 全尺寸配置未验证
- **描述**: full 配置（3840×2160）的 golden.py 和 RTL 仿真未运行
- **原因**: 数据量大（16MB/帧），仿真时间长
- **计划**: 需要长时间运行的后台仿真任务

#### P4: RTL 子模块与顶层参数传递不完整
- **描述**: top.v 定义了完整参数列表，但子模块实例化时部分参数未传递
- **影响**: frame_writer.v 和 frame_reader.v 中的 PAGE_SIZE 可能使用默认值而非配置值
- **状态**: 已修复 PAGE_SIZE 硬编码，但需验证参数传递链

#### P5: 帧头/帧尾检测的字节序一致性
- **描述**: Python 层使用小端序（struct.pack('<Q', ...)），RTL 层使用大端序移位寄存器
- **影响**: 需要确保 Golden Model 和 RTL 的帧头检测逻辑一致
- **状态**: cycle.py 已定义 FRAME_HEADER_LE，但 RTL 中需确认

### 3.3 🟢 低优先级问题

#### P6: 缺少 CRC32 正确实现
- **描述**: golden.py 中使用 MD5 前 4 字节代替 CRC32
- **影响**: 不影响功能验证，但与实际硬件不一致
- **计划**: 替换为正确的 CRC32 实现

#### P7: 缺少 Avalon-ST 握手协议完整模拟
- **描述**: DDR4 行为模型简化了 valid/ready 握手
- **影响**: 不影响功能验证，但时序仿真需要完整握手
- **计划**: 在系统级仿真中补充

#### P8: 缺少 Quartus 综合验证
- **描述**: 所有验证基于 Icarus Verilog，未用 Quartus 综合
- **影响**: 无法确认资源使用和时序约束
- **计划**: 需要 Quartus 环境

---

## 四、文件结构

```
examples/ddr_frame_buffer/
├── ARCHITECTURE.md          # 架构设计文档
├── config.py                # 可配置参数（3种配置）
├── golden.py                # Golden Model（✅ 测试通过）
├── cycle.py                 # Cycle Model（⚠️ 帧头检测 bug）
├── rtl_params.py            # RTL 参数生成
├── gen_ref.py               # 参考生成
├── gen_test_vectors.py      # 测试向量生成
├── debug_header.py          # 帧头调试
├── debug_test.py            # 调试测试
├── cycle_test_quick.py      # 快速测试
├── docs/
│   └── PROJECT_STATUS.md    # ← 本文档
├── rtl/
│   ├── top.v                # 顶层（✅ 参数化）
│   ├── page_manager.v       # 页管理器（⚠️ 硬编码）
│   ├── frame_writer.v       # 帧写入器（✅ 参数化）
│   ├── frame_reader.v       # 帧读取器（✅ 参数化）
│   ├── output_arbiter.v     # 输出仲裁器（✅ 参数化）
│   ├── command_interface.v  # 控制接口（✅ 参数化）
│   └── frame_writer_debug.v # 调试版本
├── tb_system.v              # 系统级仿真
├── tb_minimal.v             # 最小化测试
├── tb_simple.v              # 简化测试
├── tb_pm.v                  # Page Manager 测试
└── tb_ddr_frame_buffer.v    # 完整测试
```

---

## 五、下一步计划

### 5.1 短期（本周）

1. **修复 Cycle Model 帧头检测 bug**
   - 调试 cycle.py，确认帧头匹配逻辑
   - 添加单元测试验证帧头检测

2. **解决 page_manager.v 参数化问题**
   - 评估三种方案（Quartus generate / memory array / 保持硬编码）
   - 选择方案并实施

3. **验证全尺寸配置**
   - 运行 `python3 golden.py --config full`（后台任务）
   - 确认 16MB 帧数据处理正确

### 5.2 中期（本月）

4. **完善 RTL 测试平台**
   - 修复 tb_system.v 中的 page_manager 测试
   - 添加 VCD 波形分析

5. **Quartus 综合验证**
   - 创建 Quartus 工程
   - 综合并检查资源使用
   - 时序分析

6. **补充缺失功能**
   - 正确 CRC32 实现
   - 完整 Avalon-ST 握手协议
   - 帧 ID 管理

### 5.3 长期

7. **系统集成**
   - DDR4 Memory Interface IP 集成
   - Ethernet MAC 集成
   - 完整系统仿真

8. **FPGA 部署**
   - Cyclone10 开发板
   - 摄像头输入接口
   - 网络输出验证

---

## 六、Git 状态

```bash
# 最近提交
1e5e2e4 feat: RTL子模块参数化 + 修复硬编码
b5a1d0e feat: 帧尺寸参数化配置 + 修复Cycle Model帧头检测bug
c435f93 DDR帧缓冲系统: 系统级仿真运行成功
12d2391 DDR帧缓冲系统: 所有6个RTL模块编译通过
1b0c53d WIP: page_manager.v 50页版本完成（3/5测试通过）
```

---

## 七、技术决策记录

### T1: PAGE_SIZE 从 20MB 改为 16MB（Full 配置）
- **原因**: 20MB 不是 2 的幂，地址计算复杂
- **决策**: Full 配置使用 16MB 页（2 的幂），保持 50+ 页
- **状态**: 已实施

### T2: 帧头检测字节序
- **原因**: Python struct.pack('<Q', ...) 是小端序，RTL 移位寄存器是大端序
- **决策**: 定义 FRAME_HEADER_LE = 0x22DD11EE5A5A5A5A 用于移位寄存器匹配
- **状态**: cycle.py 已定义，RTL 需确认

### T3: page_manager.v 参数化方案
- **原因**: Icarus Verilog 限制
- **待决策**: 选择方案 A/B/C
- **状态**: 待讨论

---

*文档最后更新: 2026-06-29 15:15*
