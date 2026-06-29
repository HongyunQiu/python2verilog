#!/usr/bin/env python3
"""Golden Model - DDR Frame Buffer & Retransmit Manager

基于 Altera Cyclone10 + DDR4 Memory Interface IP 的行为模型
实现图像帧的多页缓冲和重发管理

设计参数：
- 图像: 3840×2160, 16bit/pixel
- 帧头: 0x5A5A5A5AEE11DD22 (8 bytes)
- 帧尾: 0x5A5A5A5AEE11DD23 (8 bytes)
- 帧大小: 16,588,816 bytes ≈ 15.83 MB
- DDR4: 1GB, 50页, 每页20MB
- 包: 4KB payload, UDP传输
"""

import struct
import time
import hashlib
from enum import IntEnum
from typing import Optional, List, Dict, Tuple

# ============================================================
# 可配置参数
# ============================================================
from config import FrameConfig, get_config

# 默认使用测试配置（小尺寸），可通过命令行参数切换
# 用法: python golden.py --config full  (使用全尺寸)
#       python golden.py --config mini  (使用最小尺寸)
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--config', choices=['mini', 'test', 'full'], default='test',
                    help='Frame configuration (mini=32x32, test=128x128, full=3840x2160)')
args, _ = parser.parse_known_args()

CFG = get_config(args.config)

# 从配置中导出常量（保持向后兼容）
FRAME_HEADER = CFG.frame_header if hasattr(CFG, 'frame_header') else 0x5A5A5A5AEE11DD22
FRAME_TRAILER = 0x5A5A5A5AEE11DD23
FRAME_HEADER_BYTES = struct.pack('<Q', FRAME_HEADER)
FRAME_TRAILER_BYTES = struct.pack('<Q', FRAME_TRAILER)

FRAME_WIDTH = CFG.frame_width
FRAME_HEIGHT = CFG.frame_height
PIXEL_BITS = CFG.pixel_bits
PIXEL_BYTES = CFG.pixel_bytes
FRAME_DATA_SIZE = CFG.frame_data_size
FRAME_TOTAL_SIZE = CFG.frame_total_size

DDR_CAPACITY = CFG.ddr_capacity
PAGE_SIZE = CFG.page_size
NUM_PAGES = CFG.num_pages

PACKET_PAYLOAD_SIZE = 4096
PACKET_HEADER_SIZE = 12
PACKET_CRC_SIZE = 4
PACKET_TOTAL_SIZE = PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE + PACKET_CRC_SIZE

PACKETS_PER_FRAME = CFG.packets_per_frame

# 包类型
PACKET_TYPE_NORMAL = 0
PACKET_TYPE_CONTROL = 1
PACKET_TYPE_RETRANSMIT = 2

# 页状态
class PageState(IntEnum):
    FREE = 0
    WRITING = 1
    READY = 2
    READING = 3


# ============================================================
# DDR4 行为模型
# ============================================================

class DDR4Model:
    """DDR4 行为模型 - 模拟 Avalon-ST 接口
    
    简化模型：
    - 内部使用 bytearray 作为存储
    - 支持按字节读写
    - 模拟 Avalon-ST 接口的 valid/ready 握手
    """
    
    def __init__(self, capacity: int = DDR_CAPACITY):
        self.capacity = capacity
        self.memory = bytearray(capacity)
        self.write_ptr = 0
        self.read_ptr = 0
        self.write_ready = True
        self.read_ready = True
        self.write_count = 0
        self.read_count = 0
        
    def write_byte(self, addr: int, data: int) -> bool:
        """写入单字节"""
        if addr >= self.capacity:
            return False
        self.memory[addr] = data & 0xFF
        self.write_count += 1
        return True
    
    def write_block(self, addr: int, data: bytes) -> bool:
        """写入数据块"""
        if addr + len(data) > self.capacity:
            return False
        self.memory[addr:addr+len(data)] = data
        self.write_count += len(data)
        return True
    
    def read_byte(self, addr: int) -> Optional[int]:
        """读取单字节"""
        if addr >= self.capacity:
            return None
        self.read_count += 1
        return self.memory[addr]
    
    def read_block(self, addr: int, size: int) -> Optional[bytes]:
        """读取数据块"""
        if addr + size > self.capacity:
            return None
        self.read_count += size
        return bytes(self.memory[addr:addr+size])
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'capacity': self.capacity,
            'write_count': self.write_count,
            'read_count': self.read_count,
        }


# ============================================================
# 页管理器
# ============================================================

class PageManager:
    """页管理器 - 管理 50 页的状态
    
    环形分配页（round-robin），支持查询页状态
    """
    
    def __init__(self, num_pages: int = NUM_PAGES, page_size: int = PAGE_SIZE):
        self.num_pages = num_pages
        self.page_size = page_size
        self.pages: List[Dict] = []
        for i in range(num_pages):
            self.pages.append({
                'page_id': i,
                'state': PageState.FREE,
                'frame_id': -1,
                'addr': i * page_size,
                'data_size': 0,
                'write_timestamp': 0,
            })
        self.next_write_page = 0  # 环形写入指针
        self.frame_counter = 0
        
    def allocate_page(self) -> Optional[int]:
        """分配一页用于写入（环形分配）
        
        返回页号，如果所有页都在使用中则返回 None
        """
        page = self.pages[self.next_write_page]
        
        # 如果当前页正在写入，尝试覆盖（丢弃旧数据）
        if page['state'] == PageState.WRITING:
            pass  # 允许覆盖
        # 如果当前页正在被读取，跳过
        elif page['state'] == PageState.READING:
            # 尝试下一页
            for i in range(1, self.num_pages):
                candidate = self.pages[(self.next_write_page + i) % self.num_pages]
                if candidate['state'] in (PageState.FREE, PageState.READY):
                    self.next_write_page = (self.next_write_page + i) % self.num_pages
                    return self._start_write(self.next_write_page)
            return None  # 所有页都在读取中
        
        return self._start_write(self.next_write_page)
    
    def _start_write(self, page_id: int) -> int:
        """开始写入指定页"""
        page = self.pages[page_id]
        page['state'] = PageState.WRITING
        page['frame_id'] = self.frame_counter
        page['data_size'] = 0
        page['write_timestamp'] = time.time()
        self.frame_counter += 1
        self.next_write_page = (page_id + 1) % self.num_pages
        return page_id
    
    def complete_write(self, page_id: int, data_size: int):
        """完成写入指定页"""
        if 0 <= page_id < self.num_pages:
            self.pages[page_id]['state'] = PageState.READY
            self.pages[page_id]['data_size'] = data_size
    
    def start_read(self, page_id: int) -> bool:
        """开始读取指定页（重发）"""
        if 0 <= page_id < self.num_pages:
            page = self.pages[page_id]
            if page['state'] == PageState.READY:
                page['state'] = PageState.READING
                return True
        return False
    
    def complete_read(self, page_id: int):
        """完成读取指定页"""
        if 0 <= page_id < self.num_pages:
            self.pages[page_id]['state'] = PageState.READY
    
    def get_page_addr(self, page_id: int) -> int:
        """获取页的起始地址"""
        if 0 <= page_id < self.num_pages:
            return self.pages[page_id]['addr']
        return -1
    
    def get_page_state(self, page_id: int) -> PageState:
        """获取页状态"""
        if 0 <= page_id < self.num_pages:
            return self.pages[page_id]['state']
        return PageState.FREE
    
    def get_page_info(self, page_id: int) -> Optional[Dict]:
        """获取页信息"""
        if 0 <= page_id < self.num_pages:
            return self.pages[page_id].copy()
        return None
    
    def get_all_page_states(self) -> List[str]:
        """获取所有页的状态字符串"""
        return [f"P{i}:{s.name}" for i, s in enumerate(
            [p['state'] for p in self.pages])]


# ============================================================
# 帧写入器
# ============================================================

class FrameWriter:
    """帧写入器 - 接收帧数据，写入 DDR
    
    帧同步：检测帧头和帧尾
    """
    
    def __init__(self, ddr: DDR4Model, page_mgr: PageManager):
        self.ddr = ddr
        self.page_mgr = page_mgr
        self.state = 'IDLE'  # IDLE, IN_FRAME
        self.current_page = -1
        self.frame_offset = 0
        self.frame_buffer = bytearray()
        
    def feed_bytes(self, data: bytes) -> Dict:
        """feeding 帧数据字节流
        
        返回处理结果：
        - {'status': 'frame_complete', 'page_id': N, 'frame_id': M}
        - {'status': 'in_progress'}
        - {'status': 'error', 'message': '...'}
        """
        for byte in data:
            self.frame_buffer.append(byte)
            
            # 检测帧头（8字节）
            if self.state == 'IDLE' and len(self.frame_buffer) >= 8:
                header = struct.unpack('<Q', bytes(self.frame_buffer[:8]))[0]
                if header == FRAME_HEADER:
                    self.state = 'IN_FRAME'
                    page_id = self.page_mgr.allocate_page()
                    if page_id is None:
                        return {'status': 'error', 'message': 'No free page'}
                    self.current_page = page_id
                    self.frame_offset = 0
                    # 不清空 buffer，保留帧头
                    continue
            
            # 检测帧尾（8字节）
            if self.state == 'IN_FRAME' and len(self.frame_buffer) >= 8:
                trailer = struct.unpack('<Q', bytes(self.frame_buffer[-8:]))[0]
                if trailer == FRAME_TRAILER:
                    # 完整帧数据（包含帧头和帧尾）
                    frame_data = bytes(self.frame_buffer)
                    addr = self.page_mgr.get_page_addr(self.current_page)
                    self.ddr.write_block(addr, frame_data)
                    self.page_mgr.complete_write(self.current_page, len(frame_data))
                    
                    frame_id = self.page_mgr.pages[self.current_page]['frame_id']
                    result = {
                        'status': 'frame_complete',
                        'page_id': self.current_page,
                        'frame_id': frame_id,
                        'data_size': len(frame_data),
                    }
                    
                    # 重置状态
                    self.state = 'IDLE'
                    self.current_page = -1
                    self.frame_offset = 0
                    self.frame_buffer.clear()
                    return result
            
            # 如果缓冲区太大但没找到帧头，清空
            if len(self.frame_buffer) > FRAME_TOTAL_SIZE + 100:
                self.frame_buffer.clear()
                self.state = 'IDLE'
        
        return {'status': 'in_progress'}


# ============================================================
# 帧读取器
# ============================================================

class FrameReader:
    """帧读取器 - 从 DDR 读取指定页的帧数据
    
    用于重发场景
    """
    
    def __init__(self, ddr: DDR4Model, page_mgr: PageManager):
        self.ddr = ddr
        self.page_mgr = page_mgr
        self.reading = False
        self.current_page = -1
        self.read_offset = 0
        self.frame_data = b''
        
    def start_read_page(self, page_id: int) -> bool:
        """开始读取指定页"""
        if self.reading:
            return False
        if not self.page_mgr.start_read(page_id):
            return False
        
        self.current_page = page_id
        self.read_offset = 0
        self.frame_data = b''
        self.reading = True
        return True
    
    def read_chunk(self, chunk_size: int = 4096) -> Optional[bytes]:
        """读取一块数据（用于分包）"""
        if not self.reading:
            return None
        
        addr = self.page_mgr.get_page_addr(self.current_page)
        page_info = self.page_mgr.get_page_info(self.current_page)
        data_size = page_info['data_size']
        
        if self.read_offset >= data_size:
            # 读取完成
            self.reading = False
            self.page_mgr.complete_read(self.current_page)
            return None
        
        remaining = data_size - self.read_offset
        actual_size = min(chunk_size, remaining)
        
        chunk = self.ddr.read_block(addr + self.read_offset, actual_size)
        self.read_offset += actual_size
        
        return chunk
    
    def read_full_frame(self) -> Optional[bytes]:
        """读取完整帧数据"""
        if not self.reading:
            return None
        
        addr = self.page_mgr.get_page_addr(self.current_page)
        page_info = self.page_mgr.get_page_info(self.current_page)
        data_size = page_info['data_size']
        
        frame_data = self.ddr.read_block(addr, data_size)
        self.reading = False
        self.page_mgr.complete_read(self.current_page)
        
        return frame_data


# ============================================================
# 包格式化器
# ============================================================

class Packetizer:
    """包格式化器 - 帧数据 → 包序列
    
    包格式：
    - 包头 (12 bytes): magic(2) + type/page_id(2) + pkt_idx(2) + frame_id(2) + offset(4)
    - Payload (4096 bytes)
    - CRC32 (4 bytes)
    """
    
    @staticmethod
    def compute_crc32(data: bytes) -> int:
        """计算 CRC32"""
        return hashlib.md5(data).digest()[:4]  # 简化版，实际用 CRC32
    
    @staticmethod
    def frame_to_packets(frame_data: bytes, page_id: int, frame_id: int) -> List[bytes]:
        """将帧数据分包"""
        packets = []
        num_packets = (len(frame_data) + PACKET_PAYLOAD_SIZE - 1) // PACKET_PAYLOAD_SIZE
        
        for i in range(num_packets):
            offset = i * PACKET_PAYLOAD_SIZE
            remaining = len(frame_data) - offset
            payload_size = min(PACKET_PAYLOAD_SIZE, remaining)
            payload = frame_data[offset:offset+payload_size]
            
            # 构建包头
            header = Packetizer._build_header(
                packet_type=PACKET_TYPE_NORMAL,
                page_id=page_id,
                packet_index=i,
                frame_id=frame_id,
                page_offset=offset
            )
            
            # 计算 CRC
            crc = Packetizer.compute_crc32(payload)
            
            # 组装包
            packet = header + payload + crc
            packets.append(packet)
        
        return packets
    
    @staticmethod
    def _build_header(packet_type: int, page_id: int, packet_index: int,
                      frame_id: int, page_offset: int) -> bytes:
        """构建包头 (12 bytes)"""
        # magic (2B) + type/page_id (2B) + pkt_idx (2B) + frame_id (2B) + offset (4B)
        magic = 0x5A5A
        type_page = (packet_type & 0x0F) | ((page_id & 0x7F) << 4)
        
        header = struct.pack('<HHHHI',
                           magic,
                           type_page,
                           packet_index & 0xFFFF,
                           frame_id & 0xFFFF,
                           page_offset & 0x1FFFFFF)
        return header
    
    @staticmethod
    def retransmit_to_packets(frame_data: bytes, page_id: int, frame_id: int,
                              start_pkt: int = 0, num_pkts: int = 0) -> List[bytes]:
        """将帧数据分包（重发模式）"""
        all_packets = Packetizer.frame_to_packets(frame_data, page_id, frame_id)
        
        if num_pkts == 0:
            num_pkts = len(all_packets) - start_pkt
        
        return all_packets[start_pkt:start_pkt+num_pkts]


# ============================================================
# 输出仲裁器
# ============================================================

class OutputArbiter:
    """输出仲裁器 - 仲裁实时流和重发流
    
    策略：重发插队，实时流继续但延迟
    - 正常：输出实时数据包
    - 重发时：重发包插入到实时流前面，实时数据缓存
    - 重发完成后：先输出缓存的实时数据，再恢复实时流
    """
    
    def __init__(self, retransmit_priority: bool = True):
        self.realtime_queue: List[bytes] = []
        self.retransmit_queue: List[bytes] = []
        self.state = 'REALTIME'  # REALTIME, RETRANSMIT
        self.realtime_buffer: List[bytes] = []  # 重发期间缓存实时数据
        self.retransmit_priority = retransmit_priority
        self.stats = {
            'realtime_packets': 0,
            'retransmit_packets': 0,
            'buffered_packets': 0,
        }
        
    def add_realtime_packet(self, packet: bytes):
        """添加实时数据包"""
        self.stats['realtime_packets'] += 1
        if self.state == 'RETRANSMIT':
            self.realtime_buffer.append(packet)
            self.stats['buffered_packets'] += 1
        else:
            self.realtime_queue.append(packet)
    
    def start_retransmit(self, packets: List[bytes]):
        """开始重发"""
        self.retransmit_queue = packets.copy()
        self.state = 'RETRANSMIT'
        self.stats['retransmit_packets'] += len(packets)
    
    def get_next_packet(self) -> Optional[bytes]:
        """获取下一个要发送的包"""
        if self.state == 'RETRANSMIT':
            if self.retransmit_queue:
                return self.retransmit_queue.pop(0)
            else:
                # 重发完成，恢复实时流
                self.state = 'REALTIME'
                # 先发送缓存的实时数据
                self.realtime_queue.extend(self.realtime_buffer)
                self.realtime_buffer.clear()
        
        if self.realtime_queue:
            return self.realtime_queue.pop(0)
        
        return None
    
    def is_empty(self) -> bool:
        """检查是否所有队列都为空"""
        return (not self.realtime_queue and 
                not self.retransmit_queue and 
                not self.realtime_buffer)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# ============================================================
# 控制接口
# ============================================================

class CommandInterface:
    """控制接口 - 接收上位机控制指令
    
    指令格式：
    - RETRANSMIT: {command: 'RETRANSMIT', page_id: N, start_pkt: M, num_pkts: K}
    - STATUS: {command: 'STATUS'}
    """
    
    def __init__(self, frame_reader: FrameReader, packetizer: Packetizer,
                 arbiter: OutputArbiter, page_mgr: PageManager):
        self.frame_reader = frame_reader
        self.packetizer = packetizer
        self.arbiter = arbiter
        self.page_mgr = page_mgr
        
    def handle_command(self, command: Dict) -> Dict:
        """处理控制指令"""
        cmd_type = command.get('command', '')
        
        if cmd_type == 'RETRANSMIT':
            return self._handle_retransmit(command)
        elif cmd_type == 'STATUS':
            return self._handle_status()
        else:
            return {'status': 'error', 'message': f'Unknown command: {cmd_type}'}
    
    def _handle_retransmit(self, command: Dict) -> Dict:
        """处理重发指令"""
        page_id = command.get('page_id', -1)
        start_pkt = command.get('start_pkt', 0)
        num_pkts = command.get('num_pkts', 0)
        
        if page_id < 0 or page_id >= self.page_mgr.num_pages:
            return {'status': 'error', 'message': f'Invalid page_id: {page_id}'}
        
        page_state = self.page_mgr.get_page_state(page_id)
        if page_state != PageState.READY:
            return {'status': 'error', 'message': f'Page {page_id} not ready (state={page_state.name})'}
        
        # 读取帧数据
        if not self.frame_reader.start_read_page(page_id):
            return {'status': 'error', 'message': f'Failed to start read page {page_id}'}
        
        frame_data = self.frame_reader.read_full_frame()
        if frame_data is None:
            return {'status': 'error', 'message': f'Failed to read page {page_id}'}
        
        # 分包
        packets = self.packetizer.retransmit_to_packets(
            frame_data, page_id, 
            self.page_mgr.pages[page_id]['frame_id'],
            start_pkt, num_pkts
        )
        
        # 插入仲裁器
        self.arbiter.start_retransmit(packets)
        
        return {
            'status': 'ok',
            'page_id': page_id,
            'packets_queued': len(packets),
        }
    
    def _handle_status(self) -> Dict:
        """返回状态信息"""
        return {
            'status': 'ok',
            'num_pages': self.page_mgr.num_pages,
            'page_states': [p['state'].name for p in self.page_mgr.pages],
            'next_write_page': self.page_mgr.next_write_page,
            'frame_counter': self.page_mgr.frame_counter,
        }


# ============================================================
# 测试
# ============================================================

def generate_test_frame(frame_id: int = 0) -> bytes:
    """生成测试帧数据"""
    frame = bytearray()
    frame.extend(FRAME_HEADER_BYTES)
    
    # 生成像素数据（简单递增模式）
    for y in range(FRAME_HEIGHT):
        for x in range(FRAME_WIDTH):
            pixel_val = (frame_id * 1000 + y * FRAME_WIDTH + x) & 0xFFFF
            frame.extend(struct.pack('<H', pixel_val))
    
    frame.extend(FRAME_TRAILER_BYTES)
    return bytes(frame)


def test_basic():
    """基础测试：写一帧 → 读一帧 → 验证"""
    print("=== DDR Frame Buffer Golden Model Test ===")
    
    # 初始化
    ddr = DDR4Model()
    page_mgr = PageManager()
    writer = FrameWriter(ddr, page_mgr)
    reader = FrameReader(ddr, page_mgr)
    packetizer = Packetizer()
    arbiter = OutputArbiter()
    cmd_if = CommandInterface(reader, packetizer, arbiter, page_mgr)
    
    # 生成测试帧
    print(f"Generating test frame (size={FRAME_TOTAL_SIZE} bytes)...")
    test_frame = generate_test_frame(frame_id=0)
    print(f"Frame size: {len(test_frame)} bytes")
    
    # 写入帧
    print("Writing frame to DDR...")
    result = writer.feed_bytes(test_frame)
    print(f"Write result: {result}")
    
    # 验证页状态
    page_id = result['page_id']
    page_info = page_mgr.get_page_info(page_id)
    print(f"Page {page_id} info: {page_info}")
    
    # 读取帧
    print(f"Reading frame from page {page_id}...")
    reader.start_read_page(page_id)
    read_frame = reader.read_full_frame()
    print(f"Read frame size: {len(read_frame)} bytes")
    
    # 验证数据一致性
    if read_frame == test_frame:
        print("✅ Frame data matches!")
    else:
        print("❌ Frame data mismatch!")
        # 找出第一个不同字节
        for i in range(min(len(read_frame), len(test_frame))):
            if read_frame[i] != test_frame[i]:
                print(f"  First difference at byte {i}: read=0x{read_frame[i]:02X}, expected=0x{test_frame[i]:02X}")
                break
    
    # 测试分包
    print(f"\nPacking frame into packets...")
    packets = packetizer.frame_to_packets(read_frame, page_id, 0)
    print(f"Number of packets: {len(packets)}")
    print(f"Expected packets: {PACKETS_PER_FRAME}")
    print(f"Packet size: {len(packets[0])} bytes")
    
    # 测试重发
    print(f"\nTesting retransmit...")
    cmd_result = cmd_if.handle_command({
        'command': 'RETRANSMIT',
        'page_id': page_id,
        'start_pkt': 0,
        'num_pkts': 10,
    })
    print(f"Retransmit result: {cmd_result}")
    
    # 从仲裁器获取包
    retransmit_packets = []
    while not arbiter.is_empty():
        pkt = arbiter.get_next_packet()
        if pkt:
            retransmit_packets.append(pkt)
    print(f"Retransmit packets from arbiter: {len(retransmit_packets)}")
    
    # 测试多帧
    print(f"\nTesting multiple frames...")
    for i in range(5):
        frame = generate_test_frame(frame_id=i+1)
        result = writer.feed_bytes(frame)
        if result['status'] == 'frame_complete':
            print(f"  Frame {i+1}: page={result['page_id']}, frame_id={result['frame_id']}")
    
    # 打印页状态
    print(f"\nPage states:")
    for i, page in enumerate(page_mgr.pages):
        if page['state'] != PageState.FREE:
            print(f"  Page {i}: {page['state'].name}, frame_id={page['frame_id']}, size={page['data_size']}")
    
    # DDR 统计
    stats = ddr.get_stats()
    print(f"\nDDR stats: {stats}")
    
    print("\n=== Test Complete ===")


if __name__ == '__main__':
    test_basic()
