# DDR Frame Buffer & Retransmit Manager

## 概述

基于 Altera Cyclone10 + DDR4 Memory Interface IP，实现图像帧的多页缓冲和重发管理器。

## 设计参数

### 图像帧
- **分辨率**: 3840 × 2160
- **位深**: 16 bit/pixel
- **帧头**: 0x5A5A5AEE11DD22 (8 bytes)
- **帧尾**: 0x5A5A5AEE11DD23 (8 bytes)
- **帧数据**: 3840 × 2160 × 2 = 16,588,800 bytes
- **总帧大小**: 16,588,816 bytes ≈ 15.83 MB

### DDR4 缓冲
- **容量**: 1 GB
- **页大小**: 20 MB (20,971,520 bytes)
- **页数**: 50 页
- **页地址对齐**: 20MB 边界

### 网络包
- **Payload**: 4096 bytes
- **包头**: 12 bytes
- **CRC32**: 4 bytes
- **总包大小**: 4112 bytes
- **每帧包数**: ceil(16,588,816 / 4096) = 4050 包

## 包格式

```
┌──────────────────────────────────────────────────────┐
│  Packet Header (12 bytes)                            │
├──────────────────────────────────────────────────────┤
│ Byte 0-1:  magic = 0x5A5A                            │
│ Byte 2:    type (4bit) + page_id (7bit) + reserved  │
│            type: 0=normal_data, 1=control, 2=retransmit │
│ Byte 3-4:  packet_index (16bit, 从帧头开始计数)       │
│ Byte 5-6:  frame_id (16bit)                          │
│ Byte 7-11: page_offset (25bit, 页内字节偏移)          │
├──────────────────────────────────────────────────────┤
│  Payload (4096 bytes)                                │
├──────────────────────────────────────────────────────┤
│  CRC32 (4 bytes)                                     │
└──────────────────────────────────────────────────────┘
```

## 数据流向

```
┌──────────┐
│ 摄像头    │
└────┬─────┘
     │ 帧数据 (带帧头帧尾)
     ▼
┌──────────────┐
│ Frame Splitter│
└──────┬───────┘
       │
  ┌────┴─────┐
  │          │
  ▼          ▼
┌──────┐  ┌──────────┐
│ Packet│  │ Frame    │
│ izer  │  │ Writer   │
└──┬───┘  └────┬─────┘
   │           │ Avalon-ST (写)
   │           ▼
   │    ┌──────────────┐
   │    │ DDR4 IP      │
   │    │ (行为模型)    │
   │    └──────┬───────┘
   │           │ Avalon-ST (读, 仅重发时)
   │           ▼
   │    ┌──────────────┐
   │    │ Frame Reader │
   │    └──────┬───────┘
   │           │
   │           ▼
   │    ┌──────────────┐
   │    │ Retransmit   │
   │    │ Packetizer   │
   │    └──────┬───────┘
   │           │
   ▼           ▼
┌─────────────────────┐
│  Output Arbiter     │
│  (实时 vs 重发)      │
└──────────┬──────────┘
           │
           ▼
    ┌──────────┐
    │ Ethernet │
    │  UDP     │
    └──────────┘
```

## 控制流

```
上位机
  │
  │ UDP 控制包 (type=1)
  │ {command: RETRANSMIT, page_id: N, start_pkt: M, num_pkts: K}
  ▼
┌──────────────┐
│ Command IF   │
│ (控制寄存器)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Page Manager │
│ (页状态管理)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Frame Reader │
│ (从DDR读页)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Output       │
│ Arbiter      │
│ (插入重发包)  │
└──────────────┘
```

## 页状态机

```
         ┌─────────┐
         │  FREE   │
         └────┬────┘
              │ 开始写入新帧
              ▼
         ┌─────────┐
         │ WRITING │
         └────┬────┘
              │ 帧写入完成
              ▼
         ┌─────────┐
         │ READY   │◄──────────────┐
         └────┬────┘               │
              │ 被重发             │ 重发完成
              ▼                    │
         ┌─────────┐               │
         │ READING │───────────────┘
         └────┬────┘
              │ 被覆盖写入新帧
              ▼
         ┌─────────┐
         │ WRITING │
         └─────────┘
```

## 模块接口

### 1. DDR4 行为模型 (ddr4_model.py)
- 模拟 DDR4 Memory Interface IP 的 Avalon 接口
- 内部使用 Python bytearray 作为存储
- 支持 Avalon-ST 读写

### 2. Page Manager (page_manager.py)
- 管理 50 页的状态
- 环形分配页（round-robin）
- 查询页状态

### 3. Frame Writer (frame_writer.py)
- 接收帧数据（带帧头帧尾）
- 通过 Avalon-ST 写入 DDR
- 帧同步（检测帧头帧尾）

### 4. Frame Reader (frame_reader.py)
- 接收重发指令（页号）
- 通过 Avalon-ST 从 DDR 读数据
- 输出帧数据流

### 5. Packetizer (packetizer.py)
- 帧数据 → 包序列
- 添加包头和 CRC

### 6. Output Arbiter (arbiter.py)
- 仲裁实时流和重发流
- 重发优先，插入式

### 7. Command IF (command_if.py)
- 接收上位机控制指令
- 解析重发请求
