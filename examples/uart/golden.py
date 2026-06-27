#!/usr/bin/env python3
"""UART Transceiver - Golden Model

纯Python实现UART收发器行为，不关心硬件。
用于验证算法正确性。

UART 帧格式（标准）：
- 空闲状态：TX 线保持高电平(1)
- 起始位：1位，低电平(0)
- 数据位：8位，LSB first
- 停止位：1位，高电平(1)

总帧长：10位（1起始 + 8数据 + 1停止）
波特率分频：每个数据位持续 baud_divider 个系统时钟周期
"""

from typing import List, Tuple


class UARTTxGolden:
    """UART 发送器 Golden Model
    
    时序：
    - 周期0: start=True, 立即输出起始位(0)
    - 周期1~baud_divider-1: 继续输出起始位(0)  [共 baud_divider 个周期]
    - 周期baud_divider: 输出数据位0
    - 每个位持续 baud_divider 个周期
    """
    
    def __init__(self, baud_divider: int = 16):
        self.baud_divider = baud_divider
        self.reset()
    
    def reset(self):
        self.tx_shift = 0
        self.tx_bit_cnt = 0
        self.tx_busy = False
        self.tx_out = 1
        self.bit_counter = 0
    
    def step(self, data_in: int, start: bool) -> int:
        if start and not self.tx_busy:
            data = data_in & 0xFF
            self.tx_shift = (1 << 9) | (data << 1)  # bit0=0, bit1-8=data, bit9=1
            self.tx_bit_cnt = 0
            self.tx_busy = True
            self.bit_counter = 0
            self.tx_out = 0  # 起始位
        
        if self.tx_busy:
            self.bit_counter += 1
            if self.bit_counter >= self.baud_divider:
                self.bit_counter = 0
                self.tx_bit_cnt += 1
                if self.tx_bit_cnt < 10:
                    self.tx_out = (self.tx_shift >> self.tx_bit_cnt) & 0x1
                else:
                    self.tx_busy = False
                    self.tx_out = 1
        
        return self.tx_out
    
    def send_byte(self, data: int) -> List[int]:
        bits = []
        total_cycles = self.baud_divider * 10
        for i in range(total_cycles):
            if i == 0:
                out = self.step(data, start=True)
            else:
                out = self.step(0, start=False)
            bits.append(out)
        return bits


class URTRxGolden:
    """UART 接收器 Golden Model
    
    时序（与发送器匹配）：
    - 周期0: rx_in=0（起始位），rx_prev初始=1，检测到下降沿
    - 起始位持续周期 0 ~ baud_divider-1
    - 数据位i 持续周期 i*baud_divider ~ (i+1)*baud_divider-1
    - 在每位中间采样：周期 i*baud_divider + baud_divider//2
    """
    
    def __init__(self, baud_divider: int = 16):
        self.baud_divider = baud_divider
        self.reset()
    
    def reset(self):
        self.rx_shift = 0
        self.rx_data = 0
        self.rx_done = False
        self.rx_frame_err = False
        self.rx_overflow = False
        self.state = 'IDLE'
        self.rx_prev = 1
        self.bit_counter = 0     # 当前位内的计数器
        self.bit_index = 0       # 当前位索引（0=起始, 1-8=数据, 9=停止）
    
    def step(self, rx_in: int) -> Tuple[int, bool, bool, bool]:
        # 注意：不在这里重置 rx_done，让它保持直到 reset()
        
        if self.state == 'IDLE':
            if self.rx_prev == 1 and rx_in == 0:
                # 检测到起始位下降沿
                self.state = 'RX'
                self.bit_counter = 1  # 已经过了1个周期
                self.bit_index = 0    # 起始位
                self.rx_shift = 0
            self.rx_prev = rx_in
            
        elif self.state == 'RX':
            self.bit_counter += 1
            if self.bit_counter >= self.baud_divider:
                self.bit_counter = 0
                self.bit_index += 1
                
            # 在每位中间采样
            sample_point = self.baud_divider // 2
            if self.bit_counter == sample_point:
                if self.bit_index == 0:
                    # 起始位采样：应该是0
                    pass  # 不检查，继续
                elif 1 <= self.bit_index <= 8:
                    # 数据位采样，LSB first
                    self.rx_shift = (self.rx_shift >> 1) | (rx_in << 7)
                elif self.bit_index == 9:
                    # 停止位采样
                    if rx_in == 1:
                        self.rx_frame_err = False
                    else:
                        self.rx_frame_err = True
            
            # 停止位结束后
            if self.bit_index == 9 and self.bit_counter >= self.baud_divider - 1:
                self.rx_data = self.rx_shift
                self.rx_done = True
                self.state = 'IDLE'
                self.rx_prev = 1
        
        return (self.rx_data, self.rx_done, self.rx_frame_err, self.rx_overflow)


class UARTGolden:
    """UART 完整收发器 Golden Model"""
    
    def __init__(self, baud_divider: int = 16):
        self.tx = UARTTxGolden(baud_divider)
        self.rx = URTRxGolden(baud_divider)
        self.baud_divider = baud_divider
    
    def loopback_test(self, data: int) -> Tuple[int, bool, bool]:
        bits = self.tx.send_byte(data)
        rx_data = 0
        rx_done = False
        rx_frame_err = False
        for bit in bits:
            rx_data, rx_done, rx_frame_err, rx_overflow = self.rx.step(bit)
        return (rx_data, rx_done, rx_frame_err)
    
    def generate_test_vectors(self) -> List[Tuple[int, int, bool]]:
        vectors = []
        for data in [0x00, 0xFF, 0xAA, 0x55, 0x12, 0xAB, 0x3C, 0xE7]:
            vectors.append((data, data, True))
        for data in [0x01, 0xFE, 0x80, 0x7F]:
            vectors.append((data, data, True))
        return vectors


if __name__ == "__main__":
    print("=== UART Golden Model 自验证 ===")
    
    uart = UARTGolden(baud_divider=16)
    vectors = uart.generate_test_vectors()
    
    all_pass = True
    for data_in, expected, should_pass in vectors:
        rx_data, rx_done, rx_frame_err = uart.loopback_test(data_in)
        status = "PASS" if (rx_data == expected and rx_done and not rx_frame_err) else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  TX=0x{data_in:02X} → RX=0x{rx_data:02X} done={rx_done} err={rx_frame_err} [{status}]")
    
    # 调试位流
    tx = UARTTxGolden(baud_divider=16)
    bits = tx.send_byte(0x55)
    print(f"\n位流 (0x55) 验证:")
    for i in range(10):
        start = i * 16
        seg = bits[start:start+16]
        val = seg[8]  # 中间采样点
        print(f"  位{i:2d}: 采样={val}, 段={seg[:4]}...{seg[12:]}")
    
    if all_pass:
        print("\n✅ Golden Model 自验证通过")
    else:
        print("\n❌ Golden Model 自验证失败")
