#!/usr/bin/env python3
"""I2C Slave - Verification Script"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden import I2CSlaveGolden
from cycle import I2CSlaveCycle


def generate_i2c_waveforms(slave_addr=0x50):
    """生成I2C波形（SCL/SDA序列）
    
    I2C时序规则：
    - SDA必须在SCL低电平时变化
    - SCL高电平时采样SDA
    - START: SCL高时SDA从高到低
    - STOP: SCL高时SDA从低到高
    """
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
        
    # 初始空闲
    idle_cycle()
    
    # 写事务
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
    
    # 读事务
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


if __name__ == "__main__":
    pass1 = test_golden_model()
    pass2 = test_golden_vs_cycle()
    
    print()
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    print(f"Golden Model自验证: {'PASS' if pass1 else 'FAIL'}")
    print(f"Golden vs Cycle: {'PASS' if pass2 else 'FAIL'}")
    
    if pass1 and pass2:
        print("所有测试通过！I2C Slave插件验证成功。")
    else:
        print("部分测试失败，需要调试。")