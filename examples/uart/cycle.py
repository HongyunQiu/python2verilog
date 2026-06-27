#!/usr/bin/env python3
"""UART Transceiver - Cycle-Accurate Model

使用框架的 CycleModel 基类，实现时序/组合逻辑分离。
"""

import sys
sys.path.insert(0, '/home/bjtc/workspace/python2verilog')
from framework import CycleModel, combinational, sequential, FixedPoint, fp

# 状态定义
IDLE = 0
RX_STATE = 1


class UARTTxCycle(CycleModel):
    """UART 发送器 Cycle Model"""
    
    def __init__(self, baud_divider=16):
        super().__init__()
        self.baud_divider = baud_divider
        self._init_regs()
    
    def _init_regs(self):
        self.reg_tx_shift = fp(0, 10)
        self.reg_tx_bit_cnt = fp(0, 4)
        self.reg_tx_busy = False
        self.reg_tx_out = 1
        self.reg_baud_cnt = fp(0, 4)
        
        self.wire_next_shift = fp(0, 10)
        self.wire_next_bit_cnt = fp(0, 4)
        self.wire_next_out = 1
        self.wire_next_baud_cnt = fp(0, 4)
        self.wire_next_busy = False
    
    @combinational
    def compute(self, data_in, start):
        if self.reset:
            self.wire_next_shift = fp(0, 10)
            self.wire_next_bit_cnt = fp(0, 4)
            self.wire_next_out = 1
            self.wire_next_baud_cnt = fp(0, 4)
            self.wire_next_busy = False
            return
        
        if start and not self.reg_tx_busy:
            data = data_in & 0xFF
            shift = (1 << 9) | (data << 1)
            self.wire_next_shift = fp(shift, 10)
            self.wire_next_bit_cnt = fp(0, 4)
            self.wire_next_busy = True
            self.wire_next_out = 0
            self.wire_next_baud_cnt = fp(0, 4)
            return
        
        if self.reg_tx_busy:
            self.wire_next_baud_cnt = self.reg_baud_cnt + 1
            
            if self.reg_baud_cnt.value + 1 >= self.baud_divider:
                self.wire_next_baud_cnt = fp(0, 4)
                self.wire_next_bit_cnt = self.reg_tx_bit_cnt + 1
                
                if self.reg_tx_bit_cnt.value + 1 < 10:
                    next_bit = (self.reg_tx_shift.value >> (self.reg_tx_bit_cnt.value + 1)) & 1
                    self.wire_next_out = next_bit
                else:
                    self.wire_next_busy = False
                    self.wire_next_out = 1
            
            self.wire_next_shift = self.reg_tx_shift
        else:
            self.wire_next_shift = self.reg_tx_shift
            self.wire_next_bit_cnt = self.reg_tx_bit_cnt
            self.wire_next_out = 1
            self.wire_next_baud_cnt = self.reg_baud_cnt
            self.wire_next_busy = False
    
    @sequential
    def clock(self):
        if self.reset:
            self._init_regs()
            return
        
        self.reg_tx_shift = self.wire_next_shift
        self.reg_tx_bit_cnt = self.wire_next_bit_cnt
        self.reg_tx_busy = self.wire_next_busy
        self.reg_tx_out = self.wire_next_out
        self.reg_baud_cnt = self.wire_next_baud_cnt
    
    def step(self, data_in, start):
        self.compute(data_in, start)
        self.clock()
        return self.wire_next_out


class URTRxCycle(CycleModel):
    """UART 接收器 Cycle Model"""
    
    def __init__(self, baud_divider=16):
        super().__init__()
        self.baud_divider = baud_divider
        self._init_regs()
    
    def _init_regs(self):
        self.reg_rx_shift = fp(0, 8)
        self.reg_rx_data = fp(0, 8)
        self.reg_rx_done = False
        self.reg_rx_frame_err = False
        self.reg_rx_state = IDLE
        self.reg_rx_bit_index = fp(0, 4)
        self.reg_rx_bit_counter = fp(0, 4)
        self.reg_rx_prev = 1
        
        self.wire_next_shift = fp(0, 8)
        self.wire_next_data = fp(0, 8)
        self.wire_next_done = False
        self.wire_next_frame_err = False
        self.wire_next_state = IDLE
        self.wire_next_bit_index = fp(0, 4)
        self.wire_next_bit_counter = fp(0, 4)
        self.wire_next_prev = 1
    
    @combinational
    def compute(self, rx_in):
        if self.reset:
            self.wire_next_shift = fp(0, 8)
            self.wire_next_data = fp(0, 8)
            self.wire_next_done = False
            self.wire_next_frame_err = False
            self.wire_next_state = IDLE
            self.wire_next_bit_index = fp(0, 4)
            self.wire_next_bit_counter = fp(0, 4)
            self.wire_next_prev = 1
            return
        
        if self.reg_rx_state == IDLE:
            falling_edge = (self.reg_rx_prev == 1) and (rx_in == 0)
            if falling_edge:
                self.wire_next_state = RX_STATE
                self.wire_next_bit_index = fp(0, 4)
                self.wire_next_bit_counter = fp(1, 4)
                self.wire_next_shift = fp(0, 8)
            else:
                self.wire_next_state = IDLE
                self.wire_next_bit_index = self.reg_rx_bit_index
                self.wire_next_bit_counter = self.reg_rx_bit_counter
                self.wire_next_shift = self.reg_rx_shift
            self.wire_next_prev = rx_in
            self.wire_next_data = self.reg_rx_data
            self.wire_next_done = False  # IDLE 时清除 done 标志
            self.wire_next_frame_err = False  # IDLE 时清除错误标志
            
        elif self.reg_rx_state == RX_STATE:
            self.wire_next_prev = rx_in
            next_counter = self.reg_rx_bit_counter.value + 1
            next_index = self.reg_rx_bit_index.value
            next_shift = self.reg_rx_shift.value
            next_data = self.reg_rx_data.value
            next_done = self.reg_rx_done
            next_frame_err = self.reg_rx_frame_err
            next_state = RX_STATE
            
            if next_counter >= self.baud_divider:
                next_counter = 0
                next_index += 1
            
            sample_point = self.baud_divider // 2
            if self.reg_rx_bit_counter.value + 1 == sample_point:
                if 1 <= self.reg_rx_bit_index.value <= 8:
                    next_shift = (next_shift >> 1) | (rx_in << 7)
                elif self.reg_rx_bit_index.value == 9:
                    if rx_in == 0:
                        next_frame_err = True
            
            if self.reg_rx_bit_index.value == 9 and next_counter >= self.baud_divider - 1:
                next_data = next_shift
                next_done = True
                next_state = IDLE
            
            self.wire_next_state = next_state
            self.wire_next_bit_index = fp(next_index, 4)
            self.wire_next_bit_counter = fp(next_counter, 4)
            self.wire_next_shift = fp(next_shift, 8)
            self.wire_next_data = fp(next_data, 8)
            self.wire_next_done = next_done
            self.wire_next_frame_err = next_frame_err
    
    @sequential
    def clock(self):
        if self.reset:
            self._init_regs()
            return
        
        self.reg_rx_shift = self.wire_next_shift
        self.reg_rx_data = self.wire_next_data
        self.reg_rx_done = self.wire_next_done
        self.reg_rx_frame_err = self.wire_next_frame_err
        self.reg_rx_state = self.wire_next_state
        self.reg_rx_bit_index = self.wire_next_bit_index
        self.reg_rx_bit_counter = self.wire_next_bit_counter
        self.reg_rx_prev = self.wire_next_prev
    
    def step(self, rx_in):
        self.compute(rx_in)
        self.clock()
        return (self.wire_next_data.value, self.wire_next_done, self.wire_next_frame_err)


class UARTCycle:
    """完整 UART Cycle Model（发送+接收）"""
    
    def __init__(self, baud_divider=16):
        self.tx = UARTTxCycle(baud_divider)
        self.rx = URTRxCycle(baud_divider)
        self.baud_divider = baud_divider
    
    def do_reset(self):
        self.tx.reset = True
        self.rx.reset = True
        self.tx.step(0, False)
        self.tx.step(0, False)
        self.tx.reset = False
        self.rx.step(1)
        self.rx.step(1)
        self.rx.reset = False
    
    def loopback_test(self, data):
        # 每次测试前重置收发器
        self.tx.reset = True
        self.rx.reset = True
        self.tx.step(0, False)
        self.rx.step(1)
        self.tx.reset = False
        self.rx.reset = False
        
        bits = []
        total_cycles = self.baud_divider * 10
        for i in range(total_cycles):
            if i == 0:
                out = self.tx.step(data, start=True)
            else:
                out = self.tx.step(0, start=False)
            bits.append(out)
        
        rx_data = 0
        rx_done = False
        rx_frame_err = False
        for bit in bits:
            rx_data, rx_done, rx_frame_err = self.rx.step(bit)
        
        # 额外一个周期让接收器回到 IDLE
        rx_data, rx_done, rx_frame_err = self.rx.step(1)
        
        return (rx_data, rx_done, rx_frame_err)


if __name__ == "__main__":
    print("=== UART Cycle Model 测试 ===")
    
    uart = UARTCycle(baud_divider=16)
    uart.do_reset()
    
    test_data = [0x00, 0xFF, 0xAA, 0x55, 0x12, 0xAB, 0x3C, 0xE7, 0x01, 0xFE, 0x80, 0x7F]
    all_pass = True
    
    for data in test_data:
        rx_data, rx_done, rx_frame_err = uart.loopback_test(data)
        status = "PASS" if (rx_data == data and rx_done and not rx_frame_err) else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  TX=0x{data:02X} → RX=0x{rx_data:02X} done={rx_done} err={rx_frame_err} [{status}]")
    
    if all_pass:
        print("\n✅ Cycle Model 测试通过")
    else:
        print("\n❌ Cycle Model 测试失败")
