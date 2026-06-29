#!/usr/bin/env python3
"""Cycle Model - DDR Frame Buffer & Retransmit Manager

基于 Python2Verilog 框架的硬件行为模拟
实现时序/组合逻辑分离，使用 FixedPoint 模拟硬件位宽
"""

import sys
import struct
import argparse
sys.path.insert(0, '/home/bjtc/workspace/python2verilog')

from typing import Optional
from framework import CycleModel, FixedPoint, fp, combinational, sequential

# ============================================================
# 可配置参数
# ============================================================
from config import (
    FRAME_HEADER, FRAME_TRAILER, FRAME_HEADER_BYTES, FRAME_TRAILER_BYTES,
    PACKET_PAYLOAD_SIZE, PACKET_HEADER_SIZE, PACKET_CRC_SIZE, PACKET_TOTAL_SIZE,
    PACKET_TYPE_NORMAL, PACKET_TYPE_CONTROL, PACKET_TYPE_RETRANSMIT,
    PAGE_STATE_FREE, PAGE_STATE_WRITING, PAGE_STATE_READY, PAGE_STATE_READING,
    get_config, ALL_CONFIGS
)

# 命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--config', choices=['mini', 'test', 'full'], default='test',
                    help='Frame configuration (mini=32x32, test=128x128, full=3840x2160)')
args, _ = parser.parse_known_args()

CFG = get_config(args.config)

# 从配置导出常量
# 注意：移位寄存器中先来的字节在高位
# FRAME_HEADER_BYTES = struct.pack('<Q', 0x5A5A5A5AEE11DD22) = b'\x22\xdd\x11\xee\x5a\x5a\x5a\x5a'
# 移位寄存器左移：先来的字节在高位 → 0x22DD11EE5A5A5A5A
FRAME_HEADER_LE = 0x22DD11EE5A5A5A5A  # 移位寄存器中帧头的值
FRAME_TRAILER_LE = 0x23DD11EE5A5A5A5A  # 移位寄存器中帧尾的值
FRAME_WIDTH = CFG.frame_width
FRAME_HEIGHT = CFG.frame_height
PIXEL_BYTES = CFG.pixel_bytes
FRAME_DATA_SIZE = CFG.frame_data_size
FRAME_TOTAL_SIZE = CFG.frame_total_size

DDR_CAPACITY = CFG.ddr_capacity
PAGE_SIZE = CFG.page_size
NUM_PAGES = CFG.num_pages

PACKETS_PER_FRAME = CFG.packets_per_frame

# 计算位宽
import math
PAGE_ID_WIDTH = max(4, (NUM_PAGES - 1).bit_length())  # 至少4bit
FRAME_OFFSET_WIDTH = max(16, (FRAME_TOTAL_SIZE - 1).bit_length())
ADDR_WIDTH = max(20, (DDR_CAPACITY - 1).bit_length())


# ============================================================
# DDR4 控制器行为模型
# ============================================================

class DDR4Controller(CycleModel):
    """DDR4 控制器行为模型
    
    模拟 Avalon-ST 接口：
    - 写接口：write_data, write_valid, write_ready, write_address
    - 读接口：read_address, read_start, read_data, read_valid, read_ready, read_last
    """
    
    def __init__(self, capacity: int = DDR_CAPACITY):
        super().__init__()
        self.capacity = capacity
        
        # 内部存储（简化为 bytearray）
        self.memory = bytearray(capacity)
        
        # 写接口信号
        self.reg_write_addr = fp(0, ADDR_WIDTH, signed=False)
        self.wire_write_data = fp(0, 8, signed=False)  # 8-bit 数据总线
        self.wire_write_valid = fp(0, 1, signed=False)
        self.wire_write_ready = fp(1, 1, signed=False)
        
        # 读接口信号
        self.reg_read_addr = fp(0, ADDR_WIDTH, signed=False)
        self.reg_read_start = fp(0, 1, signed=False)
        self.reg_read_count = fp(0, ADDR_WIDTH, signed=False)
        self.wire_read_data = fp(0, 8, signed=False)
        self.wire_read_valid = fp(0, 1, signed=False)
        self.wire_read_ready = fp(1, 1, signed=False)
        self.wire_read_last = fp(0, 1, signed=False)
        
        # 读状态机
        self.reg_read_state = fp(0, 2, signed=False)  # 0=IDLE, 1=READING
        self.reg_read_offset = fp(0, 32, signed=False)
        
        # 统计
        self.write_count = 0
        self.read_count = 0
        
    @combinational
    def compute(self, write_data: int = 0, write_valid: int = 0,
                read_start: int = 0, read_ready: int = 0):
        """组合逻辑"""
        # 写接口
        self.wire_write_data = fp(write_data & 0xFF, 8, signed=False)
        self.wire_write_valid = fp(write_valid & 1, 1, signed=False)
        self.wire_write_ready = fp(1, 1, signed=False)  # 总是 ready
        
        # 读接口
        if self.reg_read_state.value == 1:  # READING
            if self.reg_read_offset.value < self.reg_read_count.value:
                addr = self.reg_read_addr.value + self.reg_read_offset.value
                if addr < self.capacity:
                    self.wire_read_data = fp(self.memory[addr], 8, signed=False)
                    self.wire_read_valid = fp(1, 1, signed=False)
                    last = (self.reg_read_offset.value + 1 >= self.reg_read_count.value)
                    self.wire_read_last = fp(1 if last else 0, 1, signed=False)
                else:
                    self.wire_read_valid = fp(0, 1, signed=False)
                    self.wire_read_last = fp(1, 1, signed=False)
            else:
                self.wire_read_valid = fp(0, 1, signed=False)
                self.wire_read_last = fp(1, 1, signed=False)
        else:
            self.wire_read_valid = fp(0, 1, signed=False)
            self.wire_read_last = fp(0, 1, signed=False)
        
        self.wire_read_ready = fp(read_ready & 1, 1, signed=False)
        
    @sequential
    def clock(self):
        """时序逻辑"""
        # 写操作
        if self.wire_write_valid.value and self.wire_write_ready.value:
            addr = self.reg_write_addr.value
            if addr < self.capacity:
                self.memory[addr] = self.wire_write_data.value
                self.write_count += 1
            self.reg_write_addr = self.reg_write_addr + 1
        
        # 读操作
        if self.reg_read_state.value == 0:  # IDLE
            if self.reg_read_start.value:
                self.reg_read_state = fp(1, 2, signed=False)
                self.reg_read_offset = fp(0, 32, signed=False)
        elif self.reg_read_state.value == 1:  # READING
            if self.wire_read_valid.value and self.wire_read_ready.value:
                self.read_count += 1
                self.reg_read_offset = self.reg_read_offset + 1
                if self.reg_read_offset.value >= self.reg_read_count.value:
                    self.reg_read_state = fp(0, 2, signed=False)
    
    def write_byte(self, addr: int, data: int) -> bool:
        """直接写入单字节（用于初始化）"""
        if addr >= self.capacity:
            return False
        self.memory[addr] = data & 0xFF
        self.write_count += 1
        return True
    
    def write_block(self, addr: int, data: bytes) -> bool:
        """直接写入数据块（用于初始化）"""
        if addr + len(data) > self.capacity:
            return False
        self.memory[addr:addr+len(data)] = data
        self.write_count += len(data)
        return True
    
    def read_block(self, addr: int, size: int) -> Optional[bytes]:
        """直接读取数据块（用于验证）"""
        if addr + size > self.capacity:
            return None
        self.read_count += size
        return bytes(self.memory[addr:addr+size])


# ============================================================
# 页管理器
# ============================================================

class PageManager(CycleModel):
    """页管理器 - 管理 50 页的状态
    
    使用寄存器数组模拟页状态
    """
    
    def __init__(self, num_pages: int = NUM_PAGES):
        super().__init__()
        self.num_pages = num_pages
        
        # 页状态寄存器（每页 2-bit 状态）
        self.reg_page_states = [fp(PAGE_STATE_FREE, 2, signed=False) for _ in range(num_pages)]
        
        # 页帧号寄存器（每页 16-bit 帧号）
        self.reg_page_frame_ids = [fp(-1, 16, signed=True) for _ in range(num_pages)]
        
        # 环形写入指针
        self.reg_next_write_page = fp(0, 7, signed=False)
        
        # 帧计数器
        self.reg_frame_counter = fp(0, 16, signed=True)
        
        # 控制信号
        self.wire_allocate_page = fp(0, 1, signed=False)
        self.wire_complete_write = fp(0, 1, signed=False)
        self.wire_start_read = fp(0, 1, signed=False)
        self.wire_complete_read = fp(0, 1, signed=False)
        self.wire_page_id = fp(0, 7, signed=False)
        self.wire_allocated_page = fp(-1, 7, signed=True)
        self.wire_allocate_ok = fp(0, 1, signed=False)
        
    @combinational
    def compute(self, allocate: int = 0, complete_write: int = 0,
                start_read: int = 0, complete_read: int = 0,
                page_id: int = 0):
        """组合逻辑"""
        self.wire_allocate_page = fp(allocate & 1, 1, signed=False)
        self.wire_complete_write = fp(complete_write & 1, 1, signed=False)
        self.wire_start_read = fp(start_read & 1, 1, signed=False)
        self.wire_complete_read = fp(complete_read & 1, 1, signed=False)
        self.wire_page_id = fp(page_id & 0x7F, 7, signed=False)
        
        # 分配页逻辑
        if self.wire_allocate_page.value:
            candidate = self.reg_next_write_page.value
            state = self.reg_page_states[candidate].value
            if state == PAGE_STATE_READING:
                # 尝试下一页
                for i in range(1, self.num_pages):
                    next_candidate = (candidate + i) % self.num_pages
                    next_state = self.reg_page_states[next_candidate].value
                    if next_state in (PAGE_STATE_FREE, PAGE_STATE_READY):
                        self.wire_allocated_page = fp(next_candidate, 7, signed=True)
                        self.wire_allocate_ok = fp(1, 1, signed=False)
                        return
                self.wire_allocated_page = fp(-1, 7, signed=True)
                self.wire_allocate_ok = fp(0, 1, signed=False)
            else:
                self.wire_allocated_page = fp(candidate, 7, signed=True)
                self.wire_allocate_ok = fp(1, 1, signed=False)
        else:
            self.wire_allocated_page = fp(-1, 7, signed=True)
            self.wire_allocate_ok = fp(0, 1, signed=False)
    
    @sequential
    def clock(self):
        """时序逻辑"""
        # 分配页
        if self.wire_allocate_page.value and self.wire_allocate_ok.value:
            page_id = self.wire_allocated_page.value
            if 0 <= page_id < self.num_pages:
                self.reg_page_states[page_id] = fp(PAGE_STATE_WRITING, 2, signed=False)
                self.reg_page_frame_ids[page_id] = self.reg_frame_counter
                self.reg_next_write_page = fp((page_id + 1) % self.num_pages, 7, signed=False)
                self.reg_frame_counter = self.reg_frame_counter + 1
        
        # 完成写入
        if self.wire_complete_write.value:
            page_id = self.wire_page_id.value
            if 0 <= page_id < self.num_pages:
                self.reg_page_states[page_id] = fp(PAGE_STATE_READY, 2, signed=False)
        
        # 开始读取
        if self.wire_start_read.value:
            page_id = self.wire_page_id.value
            if 0 <= page_id < self.num_pages:
                if self.reg_page_states[page_id].value == PAGE_STATE_READY:
                    self.reg_page_states[page_id] = fp(PAGE_STATE_READING, 2, signed=False)
        
        # 完成读取
        if self.wire_complete_read.value:
            page_id = self.wire_page_id.value
            if 0 <= page_id < self.num_pages:
                self.reg_page_states[page_id] = fp(PAGE_STATE_READY, 2, signed=False)
    
    def get_page_state(self, page_id: int) -> int:
        """获取页状态"""
        if 0 <= page_id < self.num_pages:
            return self.reg_page_states[page_id].value
        return PAGE_STATE_FREE
    
    def get_page_frame_id(self, page_id: int) -> int:
        """获取页帧号"""
        if 0 <= page_id < self.num_pages:
            return self.reg_page_frame_ids[page_id].value
        return -1
    
    def _allocate_page(self):
        """直接执行页分配逻辑（不依赖 compute 参数）"""
        candidate = self.reg_next_write_page.value
        state = self.reg_page_states[candidate].value
        if state == PAGE_STATE_READING:
            # 尝试下一页
            for i in range(1, self.num_pages):
                next_candidate = (candidate + i) % self.num_pages
                next_state = self.reg_page_states[next_candidate].value
                if next_state in (PAGE_STATE_FREE, PAGE_STATE_READY):
                    self.wire_allocated_page = fp(next_candidate, 7, signed=True)
                    self.wire_allocate_ok = fp(1, 1, signed=False)
                    self.wire_allocate_page = fp(1, 1, signed=False)
                    self.clock()
                    return
            self.wire_allocated_page = fp(-1, 7, signed=True)
            self.wire_allocate_ok = fp(0, 1, signed=False)
        else:
            self.wire_allocated_page = fp(candidate, 7, signed=True)
            self.wire_allocate_ok = fp(1, 1, signed=False)
            self.wire_allocate_page = fp(1, 1, signed=False)
            self.clock()


# ============================================================
# 帧写入器
# ============================================================

class FrameWriter(CycleModel):
    """帧写入器 - 接收帧数据，写入 DDR
    
    帧同步：检测帧头和帧尾
    """
    
    def __init__(self, ddr: DDR4Controller, page_mgr: PageManager):
        super().__init__()
        self.ddr = ddr
        self.page_mgr = page_mgr
        
        # 状态机
        self.reg_state = fp(0, 2, signed=False)  # 0=IDLE, 1=IN_FRAME
        self.reg_current_page = fp(-1, 7, signed=True)
        self.reg_frame_offset = fp(0, 25, signed=False)
        
        # 帧头检测移位寄存器（8字节 = 64bit）
        self.reg_shift_reg = fp(0, 64, signed=False)
        self.reg_shift_count = fp(0, 7, signed=False)
        
        # 输入信号
        self.wire_input_data = fp(0, 8, signed=False)
        self.wire_input_valid = fp(0, 1, signed=False)
        
        # 输出信号
        self.wire_frame_complete = fp(0, 1, signed=False)
        self.wire_frame_page_id = fp(-1, 7, signed=True)
        self.wire_frame_id = fp(-1, 16, signed=True)
        
        # 帧缓冲区（用于存储完整帧）
        self.frame_buffer = bytearray()
        
    @combinational
    def compute(self, input_data: int = 0, input_valid: int = 0):
        """组合逻辑"""
        self.wire_input_data = fp(input_data & 0xFF, 8, signed=False)
        self.wire_input_valid = fp(input_valid & 1, 1, signed=False)
        self.wire_frame_complete = fp(0, 1, signed=False)
        
    @sequential
    def clock(self):
        """时序逻辑"""
        if not self.wire_input_valid.value:
            return
        
        data = self.wire_input_data.value
        self.frame_buffer.append(data)
        
        # 更新移位寄存器
        self.reg_shift_reg = (self.reg_shift_reg << 8) | data
        self.reg_shift_count = self.reg_shift_count + 1
        
        if self.reg_state.value == 0:  # IDLE
            if self.reg_shift_count.value >= 8:
                # shift_reg 包含最近8字节，直接与小端序帧头比较
                header = self.reg_shift_reg.value & 0xFFFFFFFFFFFFFFFF
                
                if header == FRAME_HEADER_LE:
                    self.reg_state = fp(1, 2, signed=False)
                    # 分配页
                    self.page_mgr._allocate_page()
                    if self.page_mgr.wire_allocate_ok.value:
                        self.reg_current_page = self.page_mgr.wire_allocated_page
                        self.reg_frame_offset = fp(0, 25, signed=False)
                        # 不清空 frame_buffer，保留帧头字节
                        self.reg_shift_count = fp(0, 7, signed=False)
                        self.reg_shift_reg = fp(0, 64, signed=False)
        
        elif self.reg_state.value == 1:  # IN_FRAME
            if self.reg_shift_count.value >= 8:
                trailer = self.reg_shift_reg.value & 0xFFFFFFFFFFFFFFFF
                if trailer == FRAME_TRAILER_LE:
                    # 完整帧数据
                    frame_data = bytes(self.frame_buffer)
                    page_id = self.reg_current_page.value
                    addr = page_id * PAGE_SIZE
                    self.ddr.write_block(addr, frame_data)
                    
                    # 完成写入
                    self.page_mgr.wire_complete_write = fp(1, 1, signed=False)
                    self.page_mgr.wire_page_id = fp(page_id, 7, signed=False)
                    self.page_mgr.compute()
                    self.page_mgr.clock()
                    
                    # 输出帧完成信号
                    self.wire_frame_complete = fp(1, 1, signed=False)
                    self.wire_frame_page_id = self.reg_current_page
                    self.wire_frame_id = fp(
                        self.page_mgr.get_page_frame_id(page_id), 16, signed=True)
                    
                    # 重置状态
                    self.reg_state = fp(0, 2, signed=False)
                    self.reg_current_page = fp(-1, 7, signed=True)
                    self.reg_frame_offset = fp(0, 25, signed=False)
                    self.reg_shift_count = fp(0, 7, signed=False)
                    self.reg_shift_reg = fp(0, 64, signed=False)
                    self.frame_buffer.clear()
            
            # 如果缓冲区太大但没找到帧头，清空
            if len(self.frame_buffer) > FRAME_TOTAL_SIZE + 100:
                self.frame_buffer.clear()
                self.reg_state = fp(0, 2, signed=False)
                self.reg_shift_count = fp(0, 7, signed=False)
                self.reg_shift_reg = fp(0, 64, signed=False)


# ============================================================
# 帧读取器
# ============================================================

class FrameReader(CycleModel):
    """帧读取器 - 从 DDR 读取指定页的帧数据
    
    用于重发场景
    """
    
    def __init__(self, ddr: DDR4Controller, page_mgr: PageManager):
        super().__init__()
        self.ddr = ddr
        self.page_mgr = page_mgr
        
        # 状态机
        self.reg_state = fp(0, 2, signed=False)  # 0=IDLE, 1=READING
        self.reg_page_id = fp(-1, 7, signed=True)
        self.reg_read_offset = fp(0, 25, signed=False)
        self.reg_data_size = fp(0, 25, signed=False)
        
        # 控制信号
        self.wire_start_read = fp(0, 1, signed=False)
        self.wire_page_id_in = fp(0, 7, signed=False)
        
        # 输出信号
        self.wire_read_data = fp(0, 8, signed=False)
        self.wire_read_valid = fp(0, 1, signed=False)
        self.wire_read_last = fp(0, 1, signed=False)
        self.wire_read_complete = fp(0, 1, signed=False)
        
        # 帧数据缓冲区
        self.frame_data = bytearray()
        
    @combinational
    def compute(self, start_read: int = 0, page_id: int = 0):
        """组合逻辑"""
        self.wire_start_read = fp(start_read & 1, 1, signed=False)
        self.wire_page_id_in = fp(page_id & 0x7F, 7, signed=False)
        self.wire_read_valid = fp(0, 1, signed=False)
        self.wire_read_last = fp(0, 1, signed=False)
        self.wire_read_complete = fp(0, 1, signed=False)
        
    @sequential
    def clock(self):
        """时序逻辑"""
        # 开始读取
        if self.wire_start_read.value and self.reg_state.value == 0:
            page_id = self.wire_page_id_in.value
            if self.page_mgr.get_page_state(page_id) == PAGE_STATE_READY:
                self.reg_state = fp(1, 2, signed=False)
                self.reg_page_id = fp(page_id, 7, signed=True)
                self.reg_read_offset = fp(0, 25, signed=False)
                self.frame_data.clear()
                
                # 通知页管理器开始读取
                self.page_mgr.wire_start_read = fp(1, 1, signed=False)
                self.page_mgr.wire_page_id = fp(page_id, 7, signed=False)
                self.page_mgr.clock()
        
        # 读取数据
        elif self.reg_state.value == 1:
            page_id = self.reg_page_id.value
            addr = page_id * PAGE_SIZE + self.reg_read_offset.value
            
            # 从 DDR 读取字节
            data = self.ddr.read_byte(addr)
            if data is not None:
                self.frame_data.append(data)
                self.wire_read_data = fp(data, 8, signed=False)
                self.wire_read_valid = fp(1, 1, signed=False)
                self.reg_read_offset = self.reg_read_offset + 1
                
                # 检查是否读取完成（检测帧尾）
                if len(self.frame_data) >= 8:
                    trailer = struct.unpack('<Q', bytes(self.frame_data[-8:]))[0]
                    if trailer == FRAME_TRAILER_LE:
                        self.wire_read_last = fp(1, 1, signed=False)
                        self.wire_read_complete = fp(1, 1, signed=False)
                        
                        # 通知页管理器完成读取
                        self.page_mgr.wire_complete_read = fp(1, 1, signed=False)
                        self.page_mgr.wire_page_id = fp(page_id, 7, signed=False)
                        self.page_mgr.clock()
                        
                        # 重置状态
                        self.reg_state = fp(0, 2, signed=False)
                        self.reg_page_id = fp(-1, 7, signed=True)
                        self.reg_read_offset = fp(0, 25, signed=False)


# ============================================================
# 测试
# ============================================================

def test_cycle_model():
    """测试 Cycle Model"""
    print("=== DDR Frame Buffer Cycle Model Test ===")
    
    # 初始化
    ddr = DDR4Controller()
    page_mgr = PageManager()
    writer = FrameWriter(ddr, page_mgr)
    reader = FrameReader(ddr, page_mgr)
    
    # 生成测试帧
    from golden import generate_test_frame
    test_frame = generate_test_frame(frame_id=0)
    print(f"Frame size: {len(test_frame)} bytes")
    
    # 写入帧（逐字节）
    print("Writing frame...")
    for i, byte in enumerate(test_frame):
        writer.wire_input_data = fp(byte, 8, signed=False)
        writer.wire_input_valid = fp(1, 1, signed=False)
        writer.clock()
        
        if writer.wire_frame_complete.value:
            print(f"Frame complete at byte {i}")
            print(f"  Page ID: {writer.wire_frame_page_id.value}")
            print(f"  Frame ID: {writer.wire_frame_id.value}")
            break
    
    # 验证页状态
    page_id = writer.wire_frame_page_id.value
    state = page_mgr.get_page_state(page_id)
    print(f"Page {page_id} state: {state}")
    
    # 读取帧
    print(f"Reading frame from page {page_id}...")
    reader.wire_start_read = fp(1, 1, signed=False)
    reader.wire_page_id_in = fp(page_id, 7, signed=False)
    
    read_data = bytearray()
    while not reader.wire_read_complete.value:
        reader.clock()
        if reader.wire_read_valid.value:
            read_data.append(reader.wire_read_data.value)
    
    print(f"Read {len(read_data)} bytes")
    
    # 验证数据一致性
    if bytes(read_data) == test_frame:
        print("✅ Frame data matches!")
    else:
        print("❌ Frame data mismatch!")
        for i in range(min(len(read_data), len(test_frame))):
            if read_data[i] != test_frame[i]:
                print(f"  First difference at byte {i}: read=0x{read_data[i]:02X}, expected=0x{test_frame[i]:02X}")
                break
    
    print("\n=== Test Complete ===")


if __name__ == '__main__':
    test_cycle_model()
