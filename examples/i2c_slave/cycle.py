#!/usr/bin/env python3
"""I2C Slave - Cycle-Accurate Model"""

import functools


def combinational(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._logic_type = "combinational"
    return wrapper


def sequential(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._logic_type = "sequential"
    return wrapper


IDLE = 0
ADDR = 1
DATA_RX = 2
DATA_TX = 3
ACK = 4


class I2CSlaveCycle:
    def __init__(self, slave_addr=0x50, num_regs=16):
        self.slave_addr = slave_addr & 0x7F
        self.num_regs = num_regs
        
        self.reg_state = IDLE
        self.reg_shift = 0
        self.reg_bit_cnt = 0
        self.reg_sda_prev = 1
        self.reg_scl_prev = 0
        self.reg_is_write = False
        self.reg_data = 0
        self.reg_ack = 1
        self.registers = [0] * num_regs
        self.reg_reg_ptr = 0
        
        self.wire_sda = 1
        self.wire_next_state = IDLE
        self.wire_next_shift = 0
        self.wire_next_bit_cnt = 0
        self.wire_next_data = 0
        self.wire_next_ack = 1
        self.wire_next_reg_ptr = 0
        self.wire_next_registers = [0] * num_regs
        self.wire_is_write = False
        
        self.reset = True
        
    @combinational
    def compute(self, scl, sda):
        if self.reset:
            self.wire_next_state = IDLE
            self.wire_sda = 1
            return
            
        self.wire_start = (not sda) and self.reg_sda_prev and scl and self.reg_scl_prev
        self.wire_stop = sda and (not self.reg_sda_prev) and scl and self.reg_scl_prev
        self.wire_sda = 1
        
        if self.wire_start:
            self.wire_next_state = ADDR
            self.wire_next_bit_cnt = 0
            self.wire_next_shift = 0
            
        elif self.wire_stop:
            self.wire_next_state = IDLE
            
        elif scl and (not self.reg_scl_prev):
            if self.reg_state == ADDR:
                self.wire_next_shift = (self.reg_shift << 1) | sda
                self.wire_next_bit_cnt = self.reg_bit_cnt + 1
                if self.reg_bit_cnt == 7:
                    addr = self.wire_next_shift >> 1
                    rw = self.wire_next_shift & 1
                    if addr == self.slave_addr:
                        self.wire_next_state = ACK
                        self.wire_is_write = (rw == 0)
                        self.wire_next_ack = 0
                    else:
                        self.wire_next_state = IDLE
                        self.wire_next_ack = 1
                        
            elif self.reg_state == ACK:
                if self.reg_is_write:
                    self.wire_next_state = DATA_RX
                else:
                    self.wire_next_state = DATA_TX
                self.wire_next_bit_cnt = 0
                self.wire_next_shift = 0
                
            elif self.reg_state == DATA_RX:
                self.wire_next_shift = (self.reg_shift << 1) | sda
                self.wire_next_bit_cnt = self.reg_bit_cnt + 1
                if self.reg_bit_cnt == 7:
                    self.wire_next_state = ACK
                    self.wire_next_data = self.wire_next_shift
                    self.wire_next_ack = 0
                    self.wire_next_registers = self.registers[:]
                    self.wire_next_registers[self.reg_reg_ptr] = self.wire_next_shift
                    self.wire_next_reg_ptr = (self.reg_reg_ptr + 1) % self.num_regs
                    
            elif self.reg_state == DATA_TX:
                self.wire_next_bit_cnt = self.reg_bit_cnt + 1
                if self.reg_bit_cnt == 7:
                    self.wire_next_state = ACK
                    self.wire_next_ack = 0
                    
        if self.reg_state == ACK and self.reg_bit_cnt == 0:
            self.wire_sda = self.reg_ack
            
    @sequential
    def clock(self):
        if self.reset:
            self.reg_state = IDLE
            self.reg_shift = 0
            self.reg_bit_cnt = 0
            self.reg_sda_prev = 1
            self.reg_scl_prev = 0
            self.registers = [0] * self.num_regs
            self.reg_reg_ptr = 0
            self.reg_is_write = False
            return
            
        self.reg_state = self.wire_next_state
        self.reg_shift = self.wire_next_shift
        self.reg_bit_cnt = self.wire_next_bit_cnt
        self.reg_sda_prev = self.sda_in
        self.reg_scl_prev = self.scl_in
        self.reg_data = self.wire_next_data
        self.reg_ack = self.wire_next_ack
        self.reg_reg_ptr = self.wire_next_reg_ptr
        self.reg_is_write = self.wire_is_write
        if self.wire_next_registers:
            self.registers = self.wire_next_registers[:]
            
    def step(self, scl, sda):
        self.scl_in = scl
        self.sda_in = sda
        self.compute(scl, sda)
        self.clock()
        return self.wire_sda
        
    def run_sequence(self, scl_seq, sda_seq):
        self.reset = True
        self.step(0, 1)
        self.step(0, 1)
        self.reset = False
        
        sda_out = []
        for scl, sda in zip(scl_seq, sda_seq):
            out = self.step(scl, sda)
            sda_out.append(out)
        return sda_out


if __name__ == "__main__":
    slave = I2CSlaveCycle(slave_addr=0x50)
    print("I2C Slave Cycle Model created")
    print(f"Slave address: 0x{slave.slave_addr:02X}")