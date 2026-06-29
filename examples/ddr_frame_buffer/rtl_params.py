#!/usr/bin/env python3
"""RTL 参数化接口规范

定义 Verilog 模块需要的参数、推导关系和验证逻辑
遵循 Python2Verilog 方法学：先在 Python 中验证参数正确性
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class RTLParams:
    """RTL 模块参数集"""
    
    # === 用户配置参数 ===
    frame_width: int          # 帧宽度（像素）
    frame_height: int         # 帧高度（像素）
    pixel_bits: int = 16      # 像素位深
    page_size: int = 0        # 页大小（字节），0=自动计算
    ddr_capacity: int = 0     # DDR 容量（字节），0=自动计算
    
    # === 派生参数（自动计算） ===
    pixel_bytes: int = field(init=False)
    frame_data_size: int = field(init=False)
    frame_total_size: int = field(init=False)  # 含帧头帧尾
    num_pages: int = field(init=False)
    
    # === 位宽参数 ===
    page_id_width: int = field(init=False)
    addr_width: int = field(init=False)
    frame_offset_width: int = field(init=False)
    pkt_index_width: int = field(init=False)
    frame_id_width: int = 16   # 帧号宽度（固定）
    
    # === 包参数（固定） ===
    packet_payload_size: int = 4096
    packet_header_size: int = 12
    packet_crc_size: int = 4
    packets_per_frame: int = field(init=False)
    
    # === 帧头帧尾（固定） ===
    frame_header: int = 0x5A5A5A5AEE11DD22
    frame_trailer: int = 0x5A5A5A5AEE11DD23
    
    def __post_init__(self):
        """自动计算派生参数"""
        self.pixel_bytes = self.pixel_bits // 8
        self.frame_data_size = self.frame_width * self.frame_height * self.pixel_bytes
        self.frame_total_size = self.frame_data_size + 16  # 头尾各8字节
        
        # 自动计算页大小（如果未指定）
        if self.page_size == 0:
            # 页大小 = 帧大小的向上取整到2的幂
            self.page_size = 1
            while self.page_size < self.frame_total_size:
                self.page_size *= 2
        
        # 自动计算 DDR 容量（如果未指定）
        if self.ddr_capacity == 0:
            # DDR 容量 = 页大小 * 16 页（最小）
            self.ddr_capacity = self.page_size * 16
        
        self.num_pages = self.ddr_capacity // self.page_size
        
        # 计算位宽
        self.page_id_width = max(1, (self.num_pages - 1).bit_length())
        self.addr_width = max(1, (self.ddr_capacity - 1).bit_length())
        self.frame_offset_width = max(1, (self.frame_total_size - 1).bit_length())
        self.packets_per_frame = (self.frame_total_size + self.packet_payload_size - 1) // self.packet_payload_size
        self.pkt_index_width = max(1, (self.packets_per_frame - 1).bit_length())
    
    def validate(self) -> List[str]:
        """验证参数合法性，返回错误列表"""
        errors = []
        
        # 页大小必须是2的幂
        if self.page_size & (self.page_size - 1) != 0:
            errors.append(f"page_size ({self.page_size}) must be power of 2")
        
        # 帧必须能放入一页
        if self.frame_total_size > self.page_size:
            errors.append(f"frame_total_size ({self.frame_total_size}) > page_size ({self.page_size})")
        
        # DDR 容量必须是页大小的整数倍
        if self.ddr_capacity % self.page_size != 0:
            errors.append(f"ddr_capacity ({self.ddr_capacity}) not divisible by page_size ({self.page_size})")
        
        # 至少需要2页
        if self.num_pages < 2:
            errors.append(f"num_pages ({self.num_pages}) must be >= 2")
        
        # 帧宽度必须是偶数（16bit像素对齐）
        if self.frame_width % 2 != 0:
            errors.append(f"frame_width ({self.frame_width}) must be even for 16bit pixel alignment")
        
        return errors
    
    def summary(self) -> str:
        """参数摘要"""
        return (
            f"=== RTL Parameters ===\n"
            f"Frame: {self.frame_width}x{self.frame_height} @ {self.pixel_bits}bit\n"
            f"  Data: {self.frame_data_size:,} bytes\n"
            f"  Total (with header/trailer): {self.frame_total_size:,} bytes\n"
            f"  Packets/frame: {self.packets_per_frame}\n"
            f"DDR: {self.ddr_capacity:,} bytes\n"
            f"  Page size: {self.page_size:,} bytes\n"
            f"  Num pages: {self.num_pages}\n"
            f"Widths:\n"
            f"  page_id: {self.page_id_width} bit\n"
            f"  addr: {self.addr_width} bit\n"
            f"  frame_offset: {self.frame_offset_width} bit\n"
            f"  pkt_index: {self.pkt_index_width} bit\n"
            f"======================="
        )
    
    def to_verilog_params(self) -> str:
        """生成 Verilog 参数定义字符串"""
        lines = [
            "// Auto-generated RTL parameters",
            "parameter integer FRAME_WIDTH = {},".format(self.frame_width),
            "parameter integer FRAME_HEIGHT = {},".format(self.frame_height),
            "parameter integer PIXEL_BITS = {},".format(self.pixel_bits),
            "parameter integer PIXEL_BYTES = {},".format(self.pixel_bytes),
            "parameter integer FRAME_DATA_SIZE = {},".format(self.frame_data_size),
            "parameter integer FRAME_TOTAL_SIZE = {},".format(self.frame_total_size),
            "parameter integer PAGE_SIZE = {},".format(self.page_size),
            "parameter integer NUM_PAGES = {},".format(self.num_pages),
            "parameter integer DDR_CAPACITY = {},".format(self.ddr_capacity),
            "parameter integer PAGE_ID_WIDTH = {},".format(self.page_id_width),
            "parameter integer ADDR_WIDTH = {},".format(self.addr_width),
            "parameter integer FRAME_OFFSET_WIDTH = {},".format(self.frame_offset_width),
            "parameter integer PKT_INDEX_WIDTH = {},".format(self.pkt_index_width),
            "parameter integer FRAME_ID_WIDTH = {},".format(self.frame_id_width),
            "parameter integer PACKETS_PER_FRAME = {},".format(self.packets_per_frame),
            "parameter integer PACKET_PAYLOAD_SIZE = {},".format(self.packet_payload_size),
            "parameter integer PACKET_HEADER_SIZE = {},".format(self.packet_header_size),
            "parameter integer PACKET_CRC_SIZE = {},".format(self.packet_crc_size),
            "parameter [63:0] FRAME_HEADER = 64'h5A5A5A5AEE11DD22,".format(),
            "parameter [63:0] FRAME_TRAILER = 64'h5A5A5A5AEE11DD23",
        ]
        return "\n".join(lines)


# ============================================================
# 预设配置
# ============================================================

def get_mini_config() -> RTLParams:
    """最小测试配置：32x32"""
    return RTLParams(
        frame_width=32,
        frame_height=32,
        pixel_bits=16,
        page_size=8 * 1024,       # 8KB
        ddr_capacity=256 * 1024,  # 256KB
    )

def get_test_config() -> RTLParams:
    """快速测试配置：128x128"""
    return RTLParams(
        frame_width=128,
        frame_height=128,
        pixel_bits=16,
        page_size=64 * 1024,      # 64KB
        ddr_capacity=1 * 1024 * 1024,  # 1MB
    )

def get_full_config() -> RTLParams:
    """生产配置：3840x2160"""
    return RTLParams(
        frame_width=3840,
        frame_height=2160,
        pixel_bits=16,
        page_size=16 * 1024 * 1024,     # 16MB (2的幂)
        ddr_capacity=1 * 1024 * 1024 * 1024,  # 1GB
    )


# ============================================================
# 参数推导分析
# ============================================================

def analyze_param_ranges():
    """分析不同配置下的参数范围，指导 RTL 位宽设计"""
    configs = [
        ("mini", get_mini_config()),
        ("test", get_test_config()),
        ("full", get_full_config()),
    ]
    
    print("=== Parameter Range Analysis ===\n")
    print(f"{'Param':<25} {'mini':>10} {'test':>10} {'full':>10} {'Range':>15}")
    print("-" * 75)
    
    params = [
        ('frame_width', 'Frame width'),
        ('frame_height', 'Frame height'),
        ('frame_data_size', 'Frame data (bytes)'),
        ('frame_total_size', 'Frame total (bytes)'),
        ('packets_per_frame', 'Packets/frame'),
        ('page_size', 'Page size (bytes)'),
        ('num_pages', 'Num pages'),
        ('page_id_width', 'Page ID width (bit)'),
        ('addr_width', 'Addr width (bit)'),
        ('frame_offset_width', 'Frame offset (bit)'),
        ('pkt_index_width', 'Pkt index (bit)'),
    ]
    
    for param_name, _ in params:
        values = [getattr(cfg, param_name) for _, cfg in configs]
        min_v, max_v = min(values), max(values)
        range_str = f"{min_v}-{max_v}"
        print(f"{param_name:<25} {values[0]:>10} {values[1]:>10} {values[2]:>10} {range_str:>15}")
    
    print("\n=== Validation ===")
    for name, cfg in configs:
        errors = cfg.validate()
        if errors:
            print(f"  {name}: ❌ {errors}")
        else:
            print(f"  {name}: ✅")


if __name__ == '__main__':
    analyze_param_ranges()
    
    print("\n" + get_test_config().summary())
    print("\n" + get_test_config().to_verilog_params())
