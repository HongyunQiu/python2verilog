#!/usr/bin/env python3
"""Generate reference data from Golden Model for Verilog testbench"""

import sys
import json
import struct
sys.path.insert(0, '/home/bjtc/workspace/python2verilog')

from examples.ddr_frame_buffer.golden import (
    DDR4Model, PageManager, FrameWriter, FrameReader,
    Packetizer, OutputArbiter, CommandInterface,
    FRAME_HEADER, FRAME_TRAILER, PAGE_SIZE, NUM_PAGES,
    FRAME_DATA_SIZE, FRAME_TOTAL_SIZE, generate_test_frame
)

# Create components
ddr = DDR4Model()
page_mgr = PageManager()
writer = FrameWriter(ddr, page_mgr)
reader = FrameReader(ddr, page_mgr)

# Generate and write 5 test frames
frames = []
results = []
for i in range(5):
    frame = generate_test_frame(i)
    frames.append(frame)
    result = writer.feed_bytes(frame)
    results.append(result)
    print(f"Frame {i}: size={len(frame)}, result={result['status']}", end="")
    if result['status'] == 'frame_complete':
        print(f", page={result['page_id']}, frame_id={result['frame_id']}")
    else:
        print()

# Verify page states
print("\nPage states:")
for i in range(NUM_PAGES):
    state = page_mgr.get_page_state(i)
    info = page_mgr.get_page_info(i)
    if state.name != 'FREE':
        print(f"  Page {i}: {state.name}, frame_id={info['frame_id']}, data_size={info['data_size']}")

# Test reading a frame
print("\nReading frame from page 0...")
reader.start_read_page(0)
read_data = reader.read_full_frame()
if read_data:
    print(f"  Read {len(read_data)} bytes")
    if read_data == frames[0]:
        print("  ✅ Data matches!")
    else:
        print("  ❌ Data mismatch!")
else:
    print("  ❌ Read failed")

# Generate reference data for Verilog testbench
ref_data = {
    'constants': {
        'FRAME_HEADER': f"0x{FRAME_HEADER:016X}",
        'FRAME_TRAILER': f"0x{FRAME_TRAILER:016X}",
        'PAGE_SIZE': PAGE_SIZE,
        'NUM_PAGES': NUM_PAGES,
        'FRAME_DATA_SIZE': FRAME_DATA_SIZE,
        'FRAME_TOTAL_SIZE': FRAME_TOTAL_SIZE,
    },
    'frames': [],
    'page_states': [],
    'byte_streams': []
}

for i, frame in enumerate(frames):
    ref_data['frames'].append({
        'frame_id': i,
        'page_id': results[i]['page_id'] if results[i]['status'] == 'frame_complete' else -1,
        'size': len(frame),
        'header_hex': frame[:8].hex(),
        'trailer_hex': frame[-8:].hex(),
    })
    
    # Get page state
    if results[i]['status'] == 'frame_complete':
        pid = results[i]['page_id']
        ref_data['page_states'].append({
            'page_id': pid,
            'state': page_mgr.get_page_state(pid).name,
            'frame_id': page_mgr.get_page_info(pid)['frame_id'],
        })

# Generate byte stream for first frame (for testbench stimulus)
ref_data['byte_streams'].append({
    'frame_id': 0,
    'bytes_hex': frames[0].hex(),
    'size': len(frames[0]),
})

# Save reference data
with open('/home/bjtc/workspace/python2verilog/examples/ddr_frame_buffer/golden_reference.json', 'w') as f:
    json.dump(ref_data, f, indent=2)

print(f"\nReference data saved to golden_reference.json")
print(f"Constants: FRAME_HEADER={ref_data['constants']['FRAME_HEADER']}")
print(f"           FRAME_TRAILER={ref_data['constants']['FRAME_TRAILER']}")
print(f"           PAGE_SIZE={ref_data['constants']['PAGE_SIZE']}")
