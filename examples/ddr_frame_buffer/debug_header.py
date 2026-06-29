#!/usr/bin/env python3
"""调试帧头检测"""

import sys
import struct
sys.path.insert(0, '/home/bjtc/workspace/python2verilog')

from config import get_config, FRAME_HEADER, FRAME_TRAILER, FRAME_HEADER_BYTES, FRAME_TRAILER_BYTES
from framework import fp

CFG = get_config('mini')
print(f"Config: {CFG}")
print(f"Frame total size: {CFG.frame_total_size}")

# 生成测试帧
frame = bytearray()
frame.extend(FRAME_HEADER_BYTES)
print(f"Frame header bytes: {FRAME_HEADER_BYTES.hex()}")
print(f"Frame header value (LE): {struct.unpack('<Q', FRAME_HEADER_BYTES)[0]:#018x}")

# 生成像素数据
for y in range(CFG.frame_height):
    for x in range(CFG.frame_width):
        pixel_val = (y * CFG.frame_width + x) & 0xFFFF
        frame.extend(struct.pack('<H', pixel_val))

frame.extend(FRAME_TRAILER_BYTES)
print(f"Frame trailer bytes: {FRAME_TRAILER_BYTES.hex()}")
print(f"Frame trailer value (LE): {struct.unpack('<Q', FRAME_TRAILER_BYTES)[0]:#018x}")
print(f"Total frame size: {len(frame)}")

# 模拟移位寄存器检测
print("\n=== Simulating shift register detection ===")
shift_reg = 0
shift_count = 0

for i, byte in enumerate(frame[:20]):
    shift_reg = ((shift_reg << 8) | byte) & 0xFFFFFFFFFFFFFFFF
    shift_count += 1
    
    if shift_count >= 8:
        detected = shift_reg & 0xFFFFFFFFFFFFFFFF
        print(f"Byte {i}: shift_reg={detected:#018x}, header={FRAME_HEADER:#018x}, match={detected == FRAME_HEADER}")
        if detected == FRAME_HEADER:
            print(f"✅ Frame header detected at byte {i}!")
            break

print(f"\nFRAME_HEADER constant: {FRAME_HEADER:#018x}")
print(f"Expected from bytes:  {struct.unpack('<Q', FRAME_HEADER_BYTES)[0]:#018x}")
print(f"Match: {FRAME_HEADER == struct.unpack('<Q', FRAME_HEADER_BYTES)[0]}")
