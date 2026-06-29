#!/usr/bin/env python3
"""生成 DDR Frame Buffer 测试向量"""

import struct
import random

FRAME_HEADER = 0x5A5A5A5AEE11DD22
FRAME_TRAILER = 0x5A5A5A5AEE11DD23

FRAME_WIDTH = 3840
FRAME_HEIGHT = 2160
PIXEL_BYTES = 2
FRAME_DATA_SIZE = FRAME_WIDTH * FRAME_HEIGHT * PIXEL_BYTES
FRAME_TOTAL_SIZE = FRAME_DATA_SIZE + 16  # header + trailer

def generate_frame(frame_id, size=None):
    """生成测试帧数据"""
    if size is None:
        size = FRAME_TOTAL_SIZE
    
    frame = bytearray()
    frame.extend(struct.pack('<Q', FRAME_HEADER))
    
    # 生成像素数据
    data_size = size - 16
    random.seed(frame_id)
    for i in range(data_size):
        frame.append(random.randint(0, 255))
    
    frame.extend(struct.pack('<Q', FRAME_TRAILER))
    return bytes(frame)

def generate_test_vectors():
    """生成测试向量文件"""
    # 生成 3 个测试帧
    frames = []
    for i in range(3):
        frame = generate_frame(i, size=1000)  # 小帧用于快速测试
        frames.append(frame)
        print(f"Frame {i}: {len(frame)} bytes")
    
    # 写入测试向量文件
    with open('test_vectors.txt', 'w') as f:
        f.write("// Test vectors for DDR Frame Buffer\n")
        f.write(f"// Generated {len(frames)} frames\n\n")
        
        for frame_idx, frame in enumerate(frames):
            f.write(f"// Frame {frame_idx}\n")
            for byte_idx, byte in enumerate(frame):
                f.write(f"{byte_idx} {byte}\n")
            f.write("\n")
    
    print(f"Generated test_vectors.txt with {len(frames)} frames")

if __name__ == '__main__':
    generate_test_vectors()
