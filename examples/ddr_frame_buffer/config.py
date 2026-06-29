#!/usr/bin/env python3
"""可配置参数 - DDR Frame Buffer & Retransmit Manager

支持多种帧尺寸配置：
- FULL: 3840x2160 (生产环境)
- TEST: 128x128 (快速测试)
- MINI: 32x32 (最小测试)
"""

import struct

# ============================================================
# 帧头/帧尾（固定，不受帧尺寸影响）
# ============================================================
FRAME_HEADER = 0x5A5A5A5AEE11DD22
FRAME_TRAILER = 0x5A5A5A5AEE11DD23
FRAME_HEADER_BYTES = struct.pack('<Q', FRAME_HEADER)
FRAME_TRAILER_BYTES = struct.pack('<Q', FRAME_TRAILER)

# ============================================================
# 包参数（固定）
# ============================================================
PACKET_PAYLOAD_SIZE = 4096
PACKET_HEADER_SIZE = 12
PACKET_CRC_SIZE = 4
PACKET_TOTAL_SIZE = PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE + PACKET_CRC_SIZE

# 包类型
PACKET_TYPE_NORMAL = 0
PACKET_TYPE_CONTROL = 1
PACKET_TYPE_RETRANSMIT = 2

# 页状态
PAGE_STATE_FREE = 0
PAGE_STATE_WRITING = 1
PAGE_STATE_READY = 2
PAGE_STATE_READING = 3


# ============================================================
# 配置类
# ============================================================

class FrameConfig:
    """帧配置类，支持动态计算派生参数"""
    
    def __init__(self, name: str, frame_width: int, frame_height: int,
                 pixel_bits: int, ddr_capacity: int, page_size: int,
                 description: str = ''):
        self.name = name
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.pixel_bits = pixel_bits
        self.pixel_bytes = pixel_bits // 8
        
        # 派生参数
        self.frame_data_size = frame_width * frame_height * (pixel_bits // 8)
        self.frame_total_size = self.frame_data_size + 16  # 头尾各8字节
        
        self.ddr_capacity = ddr_capacity
        self.page_size = page_size
        self.num_pages = ddr_capacity // page_size
        
        # 包数计算
        self.packets_per_frame = (self.frame_total_size + PACKET_PAYLOAD_SIZE - 1) // PACKET_PAYLOAD_SIZE
        
        self.description = description
    
    def __repr__(self):
        return (f"FrameConfig({self.name}, {self.frame_width}x{self.frame_height}, "
                f"{self.frame_total_size}B/frame, {self.num_pages} pages)")


# ============================================================
# 预设配置
# ============================================================

CONFIG_MINI = FrameConfig(
    name='mini',
    frame_width=32,
    frame_height=32,
    pixel_bits=16,
    ddr_capacity=256 * 1024,  # 256KB
    page_size=8 * 1024,  # 8KB
    description='Minimal test config (32x32, ~2KB/frame)',
)

CONFIG_TEST = FrameConfig(
    name='test',
    frame_width=128,
    frame_height=128,
    pixel_bits=16,
    ddr_capacity=1 * 1024 * 1024,  # 1MB
    page_size=64 * 1024,  # 64KB
    description='Quick test config (128x128, ~32KB/frame)',
)

CONFIG_FULL = FrameConfig(
    name='full',
    frame_width=3840,
    frame_height=2160,
    pixel_bits=16,
    ddr_capacity=1 * 1024 * 1024 * 1024,  # 1GB
    page_size=16 * 1024 * 1024,  # 16MB (2的幂，原20MB不是2的幂)
    description='Full resolution 4K production config (16MB pages)',
)

# 配置字典
ALL_CONFIGS = {
    'mini': CONFIG_MINI,
    'test': CONFIG_TEST,
    'full': CONFIG_FULL,
}

# 默认配置
DEFAULT_CONFIG = CONFIG_TEST


def get_config(name: str = 'test') -> FrameConfig:
    """获取配置"""
    if name in ALL_CONFIGS:
        return ALL_CONFIGS[name]
    raise ValueError(f"Unknown config: {name}. Available: {list(ALL_CONFIGS.keys())}")


if __name__ == '__main__':
    print("Available configurations:")
    for name, cfg in ALL_CONFIGS.items():
        print(f"  {name:6s}: {cfg}")
        print(f"           Frame: {cfg.frame_total_size:,} bytes, "
              f"Packets/frame: {cfg.packets_per_frame}, "
              f"Pages: {cfg.num_pages}")
