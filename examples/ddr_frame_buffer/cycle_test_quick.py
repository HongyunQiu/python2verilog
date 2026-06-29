#!/usr/bin/env python3
"""快速测试 Cycle Model - 只测试帧写入（跳过读取）

用于验证基本功能，避免逐字节仿真超时
"""

import sys
import struct
import time
sys.path.insert(0, '/home/bjtc/workspace/python2verilog')

from config import get_config, FRAME_HEADER_BYTES, FRAME_TRAILER_BYTES, FRAME_HEADER, FRAME_TRAILER

# 支持命令行参数
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--config', choices=['mini', 'test', 'full'], default='mini',
                    help='Frame configuration')
args, _ = parser.parse_known_args()
CFG = get_config(args.config)
print(f"Config: {CFG}")
print(f"Frame size: {CFG.frame_total_size} bytes")
print(f"Pages: {CFG.num_pages}, Page size: {CFG.page_size}")

from framework import fp

# 导入 cycle model 模块
sys.argv = ['cycle_test_quick.py', '--config', 'mini']
from cycle import (
    DDR4Controller, PageManager, FrameWriter,
    FRAME_HEADER_LE, FRAME_TRAILER_LE, PAGE_SIZE, NUM_PAGES
)

def test_write_only():
    """只测试帧写入，验证帧头尾检测和页分配"""
    print("\n=== Quick Cycle Model Test (Write Only) ===")
    
    # 初始化
    ddr = DDR4Controller(capacity=CFG.ddr_capacity)
    page_mgr = PageManager(num_pages=CFG.num_pages)
    writer = FrameWriter(ddr, page_mgr)
    
    # 生成测试帧
    frame = bytearray()
    frame.extend(FRAME_HEADER_BYTES)
    for i in range(CFG.frame_data_size):
        frame.append(i & 0xFF)
    frame.extend(FRAME_TRAILER_BYTES)
    frame = bytes(frame)
    print(f"Test frame: {len(frame)} bytes")
    
    # 逐字节写入
    print("Writing frame byte by byte...")
    start = time.time()
    
    frame_complete = False
    for i, byte in enumerate(frame):
        writer.wire_input_data = fp(byte, 8, signed=False)
        writer.wire_input_valid = fp(1, 1, signed=False)
        writer.clock()
        
        if writer.wire_frame_complete.value:
            frame_complete = True
            elapsed = time.time() - start
            print(f"✅ Frame complete at byte {i}")
            print(f"   Page ID: {writer.wire_frame_page_id.value}")
            print(f"   Frame ID: {writer.wire_frame_id.value}")
            print(f"   Time: {elapsed:.2f}s, Speed: {len(frame)/elapsed:.0f} bytes/s")
            break
    
    if not frame_complete:
        print("❌ Frame not complete!")
        return False
    
    # 验证页状态
    page_id = writer.wire_frame_page_id.value
    state = page_mgr.get_page_state(page_id)
    print(f"\nPage {page_id} state: {state}")
    
    # 验证 DDR 数据
    addr = page_id * PAGE_SIZE
    ddr_data = ddr.read_block(addr, len(frame))
    if ddr_data == frame:
        print("✅ DDR data matches!")
    else:
        print("❌ DDR data mismatch!")
        for i in range(min(len(ddr_data), len(frame))):
            if ddr_data[i] != frame[i]:
                print(f"  First diff at byte {i}: ddr=0x{ddr_data[i]:02X}, expected=0x{frame[i]:02X}")
                break
    
    return True


def test_multiple_frames():
    """测试多帧写入"""
    print("\n=== Multiple Frames Test ===")
    
    ddr = DDR4Controller(capacity=CFG.ddr_capacity)
    page_mgr = PageManager(num_pages=CFG.num_pages)
    writer = FrameWriter(ddr, page_mgr)
    
    # 生成小帧
    frame = bytearray()
    frame.extend(FRAME_HEADER_BYTES)
    for i in range(CFG.frame_data_size):
        frame.append(i & 0xFF)
    frame.extend(FRAME_TRAILER_BYTES)
    frame = bytes(frame)
    
    num_frames = min(5, CFG.num_pages)  # 不超过页数
    print(f"Writing {num_frames} frames...")
    
    for fid in range(num_frames):
        writer2 = FrameWriter(ddr, page_mgr)
        for byte in frame:
            writer2.wire_input_data = fp(byte, 8, signed=False)
            writer2.wire_input_valid = fp(1, 1, signed=False)
            writer2.clock()
            if writer2.wire_frame_complete.value:
                pid = writer2.wire_frame_page_id.value
                fid_out = writer2.wire_frame_id.value
                print(f"  Frame {fid}: page={pid}, frame_id={fid_out}")
                break
    
    # 打印页状态
    print("\nPage states:")
    for i in range(CFG.num_pages):
        state = page_mgr.get_page_state(i)
        if state != 0:  # not FREE
            fid = page_mgr.get_page_frame_id(i)
            print(f"  Page {i}: state={state}, frame_id={fid}")
    
    return True


if __name__ == '__main__':
    success = test_write_only()
    if success:
        test_multiple_frames()
    print("\n=== Test Complete ===")
