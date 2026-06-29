#!/usr/bin/env python3
"""调试 test 配置帧写入"""

import sys
import struct
import time
sys.path.insert(0, '/home/bjtc/workspace/python2verilog')

from config import get_config, FRAME_HEADER_BYTES, FRAME_TRAILER_BYTES
from framework import fp

# 使用 test 配置
sys.argv = ['debug_test.py', '--config', 'test']
from cycle import (
    DDR4Controller, PageManager, FrameWriter,
    FRAME_HEADER_LE, FRAME_TRAILER_LE, PAGE_SIZE, NUM_PAGES, FRAME_TOTAL_SIZE
)

CFG = get_config('test')
print(f"Config: {CFG}")
print(f"Frame total size: {CFG.frame_total_size}")
print(f"NUM_PAGES={NUM_PAGES}, PAGE_SIZE={PAGE_SIZE}")
print(f"FRAME_HEADER_LE={FRAME_HEADER_LE:#018x}")
print(f"FRAME_TRAILER_LE={FRAME_TRAILER_LE:#018x}")

# 生成测试帧
frame = bytearray()
frame.extend(FRAME_HEADER_BYTES)
for y in range(CFG.frame_height):
    for x in range(CFG.frame_width):
        pixel_val = (y * CFG.frame_width + x) & 0xFFFF
        frame.extend(struct.pack('<H', pixel_val))
frame.extend(FRAME_TRAILER_BYTES)
frame = bytes(frame)
print(f"Test frame: {len(frame)} bytes")

# 初始化
ddr = DDR4Controller(capacity=CFG.ddr_capacity)
page_mgr = PageManager(num_pages=CFG.num_pages)
writer = FrameWriter(ddr, page_mgr)

# 逐字节写入
print("\nWriting frame...")
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
    
    # 调试输出：每1000字节打印一次状态
    if i % 1000 == 0 and i < 100:
        print(f"  Byte {i}: state={writer.reg_state.value}, shift_count={writer.reg_shift_count.value}, buf_len={len(writer.frame_buffer)}")

if not frame_complete:
    print(f"❌ Frame not complete!")
    print(f"  Final state: {writer.reg_state.value}")
    print(f"  Shift count: {writer.reg_shift_count.value}")
    print(f"  Buffer length: {len(writer.frame_buffer)}")
    print(f"  Current page: {writer.reg_current_page.value}")
    
    # 检查帧尾检测
    if len(writer.frame_buffer) >= 8:
        last8 = bytes(writer.frame_buffer[-8:])
        trailer_detected = struct.unpack('<Q', last8)[0]
        print(f"  Last 8 bytes: {last8.hex()}")
        print(f"  Trailer detected: {trailer_detected:#018x}")
        print(f"  Expected: {FRAME_TRAILER_LE:#018x}")
        print(f"  Match: {trailer_detected == FRAME_TRAILER_LE}")
