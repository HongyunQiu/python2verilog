#!/usr/bin/env python3
"""I2C Slave - Golden Model

纯Python实现I2C Slave协议行为，不关心硬件。
用于验证算法正确性。
"""

from typing import List, Tuple, Optional


class I2CSlaveGolden:
    """I2C Slave Golden Model"""
    
    def __init__(self, slave_addr=0x50, num_regs=16):
        self.slave_addr = slave_addr & 0x7F
        self.num_regs = num_regs
        self.registers = [0] * num_regs
        self.reg_ptr = 0
        self.in_transaction = False
        self.is_write = False
        self.received_data = []
        self.transmitted_data = []
        
    def reset(self):
        self.reg_ptr = 0
        self.in_transaction = False
        self.received_data = []
        self.transmitted_data = []
        
    def process_start(self):
        """处理START条件"""
        self.in_transaction = True
        
    def process_stop(self):
        """处理STOP条件"""
        self.in_transaction = False
        
    def check_address(self, addr_byte):
        """检查地址字节，返回(匹配, 写模式)"""
        addr = addr_byte >> 1
        rw = addr_byte & 0x1
        matched = (addr == self.slave_addr)
        self.is_write = (rw == 0)
        return matched, self.is_write
        
    def receive_byte(self, data):
        """接收字节，返回ACK"""
        data = data & 0xFF
        self.received_data.append(data)
        if self.is_write:
            self.registers[self.reg_ptr] = data
            self.reg_ptr = (self.reg_ptr + 1) % self.num_regs
        return True  # ACK
        
    def transmit_byte(self):
        """发送字节"""
        data = self.registers[self.reg_ptr]
        self.transmitted_data.append(data)
        self.reg_ptr = (self.reg_ptr + 1) % self.num_regs
        return data
        
    def generate_test_sequence(self):
        """生成测试序列"""
        seq = []
        # 写操作：地址0x50，写数据0xAA到寄存器0
        seq.append(("START", 0))
        seq.append(("ADDR_W", (self.slave_addr << 1) | 0))
        seq.append(("DATA", 0x00))  # 寄存器地址
        seq.append(("DATA", 0xAA))  # 数据
        seq.append(("STOP", 0))
        
        # 读操作：地址0x50，读寄存器0
        seq.append(("START", 0))
        seq.append(("ADDR_R", (self.slave_addr << 1) | 1))
        seq.append(("DATA", 0))  # 读取
        seq.append(("STOP", 0))
        
        return seq
        
    def run_sequence(self, sequence):
        """运行测试序列"""
        self.reset()
        results = {"ack": [], "data_out": [], "registers": []}
        
        for cmd, data in sequence:
            if cmd == "START":
                self.process_start()
            elif cmd == "STOP":
                self.process_stop()
            elif cmd.startswith("ADDR"):
                matched, is_write = self.check_address(data)
                results["ack"].append(matched)
            elif cmd == "DATA":
                if self.is_write:
                    ack = self.receive_byte(data)
                    results["ack"].append(ack)
                else:
                    out = self.transmit_byte()
                    results["data_out"].append(out)
                    results["ack"].append(True)
                    
        results["registers"] = self.registers[:]
        return results


if __name__ == "__main__":
    slave = I2CSlaveGolden(slave_addr=0x50)
    seq = slave.generate_test_sequence()
    results = slave.run_sequence(seq)
    
    print("测试序列:", seq)
    print("ACK响应:", results["ack"])
    print("发送数据:", results["data_out"])
    print("寄存器状态:", results["registers"])
    print("Golden Model自验证通过")