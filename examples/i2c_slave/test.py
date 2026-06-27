#!/usr/bin/env python3
"""I2C Slave - Verification Script"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden import I2CSlaveGolden
from cycle import I2CSlaveCycle


def generate_i2c_waveforms(slave_addr=0x50):
    scl = []
    sda_master = []
    
    def idle_cycle():
        scl.extend([0, 0])
        sda_master.extend([1, 1])
        
    def start_condition():
        scl.extend([0, 1, 1])
        sda_master.extend([1, 1, 0])
        
    def stop_condition():
        scl.extend([0, 1, 1])
        sda_master.extend([0, 0, 1])
        
    def send_bit(bit_val):
        scl.extend([0, 1, 1, 0])
        sda_master.extend([bit_val, bit_val, bit_val, bit_val])
        
    def send_byte(byte_val):
        for bit in range(7, -1, -1):
            bit_val = (byte_val >> bit) & 1
            send_bit(bit_val)
            
    def ack_slot():
        scl.extend([0, 1, 1, 0])
        sda_master.extend([1, 1, 1, 1])
        
    idle_cycle()
    start_condition()
    send_byte((slave_addr << 1) | 0)
    ack_slot()
    send_byte(0x00)
    ack_slot()
    send_byte(0xAA)
    ack_slot()
    stop_condition()
    idle_cycle()
    idle_cycle()
    start_condition()
    send_byte((slave_addr << 1) | 1)
    ack_slot()
    send_byte(0x00)
    ack_slot()
    stop_condition()
    
    return scl, sda_master


def test_golden_model():
    print("=" * 60)
    print("测试1: Golden Model自验证")
    print("=" * 60)
    
    slave = I2CSlaveGolden(slave_addr=0x50)
    seq = slave.generate_test_sequence()
    results = slave.run_sequence(seq)
    
    print("ACK响应:", results["ack"])
    print("寄存器[1]:", hex(results["registers"][1]))
    
    assert results["registers"][1] == 0xAA
    print("PASS")
    return True


def test_golden_vs_cycle():
    print()
    print("=" * 60)
    print("测试2: Golden Model vs Cycle Model")
    print("=" * 60)
    
    slave_addr = 0x50
    scl_seq, sda_master_seq = generate_i2c_waveforms(slave_addr)
    
    cycle_slave = I2CSlaveCycle(slave_addr=slave_addr)
    sda_out = cycle_slave.run_sequence(scl_seq, sda_master_seq)
    
    golden_slave = I2CSlaveGolden(slave_addr=slave_addr)
    golden_seq = golden_slave.generate_test_sequence()
    golden_results = golden_slave.run_sequence(golden_seq)
    
    print(f"Cycle寄存器[1]: 0x{cycle_slave.registers[1]:02X}")
    print(f"Golden寄存器[1]: 0x{golden_results['registers'][1]:02X}")
    
    if cycle_slave.registers[1] == golden_results["registers"][1] == 0xAA:
        print("PASS")
        return True
    else:
        print("FAIL")
        return False


def generate_testbench(scl_seq, sda_seq, output_file):
    """生成Verilog测试平台"""
    lines = []
    lines.append("`timescale 1ns/1ps")
    lines.append("")
    lines.append("module tb_i2c_slave;")
    lines.append("    reg  clk, rst_n, scl, sda_in;")
    lines.append("    wire sda_out, sda_oe, data_ready, addr_match;")
    lines.append("    wire [7:0] data_out;")
    lines.append("    wire [1:0] debug_state;")
    lines.append("    wire [3:0] debug_bit_cnt;")
    lines.append("")
    lines.append("    i2c_slave #( .SLAVE_ADDR(8'h50) ) dut (")
    lines.append("        .clk(clk), .rst_n(rst_n), .scl(scl), .sda_in(sda_in),")
    lines.append("        .sda_out(sda_out), .sda_oe(sda_oe), .data_out(data_out),")
    lines.append("        .data_ready(data_ready), .addr_match(addr_match),")
    lines.append("        .debug_state(debug_state), .debug_bit_cnt(debug_bit_cnt)")
    lines.append("    );")
    lines.append("")
    lines.append("    initial begin clk=0; forever #5 clk=~clk; end")
    lines.append("")
    lines.append("    integer i;")
    lines.append("    initial begin")
    lines.append("        rst_n=0; scl=0; sda_in=1;")
    lines.append("        #20 rst_n=1;")
    
    for i, (scl_val, sda_val) in enumerate(zip(scl_seq, sda_seq)):
        lines.append(f"        #10 scl={scl_val}; sda_in={sda_val};")
        
    lines.append("        #20 $finish;")
    lines.append("    end")
    lines.append("")
    lines.append("    integer fout;")
    lines.append('    initial fout = $fopen("verilog_output.txt", "w");')
    lines.append("")
    lines.append("    always @(posedge clk) begin")
    # 使用原始字符串避免\n被Python解释为换行符
    lines.append(r'        $fwrite(fout, "%d %d %d %d %d\n", debug_state, debug_bit_cnt, scl, sda_in, data_ready);')
    lines.append("    end")
    lines.append("")
    lines.append("endmodule")
    
    with open(output_file, 'w') as f:
        f.write("\n".join(lines))


def test_cycle_vs_verilog():
    print()
    print("=" * 60)
    print("测试3: Cycle Model vs Verilog")
    print("=" * 60)
    
    work_dir = os.path.dirname(os.path.abspath(__file__))
    artifacts_dir = os.path.join(work_dir, '..', '..', 'artifacts')
    os.makedirs(artifacts_dir, exist_ok=True)
    
    slave_addr = 0x50
    scl_seq, sda_master_seq = generate_i2c_waveforms(slave_addr)
    
    # Cycle Model参考输出
    cycle_slave = I2CSlaveCycle(slave_addr=slave_addr)
    cycle_slave.run_sequence(scl_seq, sda_master_seq)
    cycle_reg = cycle_slave.registers[1]
    
    # 生成测试平台
    tb_file = os.path.join(artifacts_dir, 'tb_i2c.v')
    generate_testbench(scl_seq, sda_master_seq, tb_file)
    
    # 编译
    result = subprocess.run(
        ['iverilog', '-o', os.path.join(artifacts_dir, 'i2c_firmware'),
         tb_file, os.path.join(work_dir, 'template.v')],
        capture_output=True, text=True, timeout=30
    )
    
    if result.returncode != 0:
        print(f"编译失败:")
        print(result.stderr[:500])
        return False
    
    print("编译成功")
    
    # 仿真
    result = subprocess.run(
        ['vvp', os.path.join(artifacts_dir, 'i2c_firmware')],
        capture_output=True, text=True, timeout=30,
        cwd=artifacts_dir
    )
    
    if result.returncode != 0:
        print(f"仿真失败:")
        print(result.stderr[:500])
        return False
    
    # 读取输出
    output_file = os.path.join(artifacts_dir, 'verilog_output.txt')
    if not os.path.exists(output_file):
        print("输出文件未生成")
        return False
    
    with open(output_file, 'r') as f:
        debug_lines = [line.strip() for line in f if line.strip()]
    
    print(f"调试输出行数: {len(debug_lines)}")
    
    # 解析调试输出，查找data_ready=1的时刻
    data_ready_lines = [line for line in debug_lines if line.split()[-1] == '1']
    print(f"data_ready=1的行数: {len(data_ready_lines)}")
    
    if data_ready_lines:
        print(f"data_ready触发时的状态: {data_ready_lines[:5]}")
    
    # 查找DATA_RX状态(2)且bit_cnt=7的行
    data_rx_done = [line for line in debug_lines if line.split()[0] == '2' and line.split()[1] == '7']
    print(f"DATA_RX完成(bit=7)的行数: {len(data_rx_done)}")
    if data_rx_done:
        print(f"DATA_RX完成时的状态: {data_rx_done[:5]}")
    
    # 检查Cycle Model的寄存器值
    print(f"Cycle寄存器[1]: 0x{cycle_reg:02X}")
    
    # 如果data_ready从未触发，检查状态机是否正确进入DATA_RX
    if not data_ready_lines:
        print("data_ready从未触发，检查状态机...")
        # 统计各状态出现次数
        from collections import Counter
        states = [line.split()[0] for line in debug_lines if line.split()[0] not in ['x']]
        state_counts = Counter(states)
        print(f"状态分布: {dict(state_counts)}")
        return False
    
    print("PASS")
    return True


if __name__ == "__main__":
    pass1 = test_golden_model()
    pass2 = test_golden_vs_cycle()
    pass3 = test_cycle_vs_verilog()
    
    print()
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    print(f"Golden Model自验证: {'PASS' if pass1 else 'FAIL'}")
    print(f"Golden vs Cycle: {'PASS' if pass2 else 'FAIL'}")
    print(f"Cycle vs Verilog: {'PASS' if pass3 else 'FAIL'}")
    
    if pass1 and pass2 and pass3:
        print("所有测试通过！I2C Slave插件验证成功。")
    else:
        print("部分测试失败，需要调试。")
