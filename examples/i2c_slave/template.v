// I2C Slave - Verilog Template
// 
// 从Cycle Model自动生成的Verilog实现
// 与Python Cycle Model逐位精确匹配
//
// 状态机：IDLE/ADDR/DATA_RX/DATA_TX/ACK

module i2c_slave #(
    parameter SLAVE_ADDR = 8'h50,
    parameter NUM_REGS   = 16
)(
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    scl,
    input  wire                    sda_in,
    output reg                     sda_out,
    output reg                     sda_oe,       // SDA输出使能
    output reg [7:0]               data_out,
    output reg                     data_ready,
    output reg                     addr_match,
    // 调试输出（仅用于验证）
    output reg [1:0]               debug_state,
    output reg [3:0]               debug_bit_cnt
);

    // 状态编码
    localparam IDLE    = 2'd0;
    localparam ADDR    = 2'd1;
    localparam DATA_RX = 2'd2;
    localparam DATA_TX = 2'd3;
    localparam ACK     = 2'd4;

    // 寄存器（时序逻辑）
    reg [1:0]          reg_state;
    reg [7:0]          reg_shift;
    reg [3:0]          reg_bit_cnt;
    reg                reg_sda_prev;
    reg                reg_scl_prev;
    reg                reg_is_write;
    reg [7:0]          reg_data;
    reg                reg_ack;
    reg [7:0]          reg_registers [0:NUM_REGS-1];
    reg [3:0]          reg_reg_ptr;

    // 组合逻辑中间值
    wire               wire_start;
    wire               wire_stop;
    reg [1:0]          wire_next_state;
    reg [7:0]          wire_next_shift;
    reg [3:0]          wire_next_bit_cnt;
    reg                wire_next_ack;
    reg [3:0]          wire_next_reg_ptr;
    reg                wire_is_write;

    // START/STOP检测（组合逻辑）
    assign wire_start = (!sda_in) && reg_sda_prev && scl && reg_scl_prev;
    assign wire_stop  = sda_in && (!reg_sda_prev) && scl && reg_scl_prev;

    // 组合逻辑：状态解码
    always @(*) begin
        wire_next_state = reg_state;
        wire_next_shift = reg_shift;
        wire_next_bit_cnt = reg_bit_cnt;
        wire_next_ack = reg_ack;
        wire_next_reg_ptr = reg_reg_ptr;
        wire_is_write = reg_is_write;

        if (!rst_n) begin
            wire_next_state = IDLE;
        end else if (wire_start) begin
            wire_next_state = ADDR;
            wire_next_bit_cnt = 4'd0;
            wire_next_shift = 8'd0;
        end else if (wire_stop) begin
            wire_next_state = IDLE;
        end else if (scl && !reg_scl_prev) begin
            case (reg_state)
                ADDR:
                    begin
                        wire_next_shift = {reg_shift[6:0], sda_in};
                        wire_next_bit_cnt = reg_bit_cnt + 1'd1;
                        if (reg_bit_cnt == 7) begin
                            if ((wire_next_shift[7:1] == SLAVE_ADDR[6:0])) begin
                                wire_next_state = ACK;
                                wire_is_write = !sda_in;
                                wire_next_ack = 1'b0;
                            end else begin
                                wire_next_state = IDLE;
                                wire_next_ack = 1'b1;
                            end
                        end
                    end

                ACK:
                    begin
                        if (reg_is_write)
                            wire_next_state = DATA_RX;
                        else
                            wire_next_state = DATA_TX;
                        wire_next_bit_cnt = 4'd0;
                        wire_next_shift = 8'd0;
                    end

                DATA_RX:
                    begin
                        wire_next_shift = {reg_shift[6:0], sda_in};
                        wire_next_bit_cnt = reg_bit_cnt + 1'd1;
                        if (reg_bit_cnt == 7) begin
                            wire_next_state = ACK;
                            wire_next_ack = 1'b0;
                            wire_next_reg_ptr = (reg_reg_ptr + 1) % NUM_REGS;
                        end
                    end

                DATA_TX:
                    begin
                        wire_next_bit_cnt = reg_bit_cnt + 1'd1;
                        if (reg_bit_cnt == 7) begin
                            wire_next_state = ACK;
                            wire_next_ack = 1'b0;
                        end
                    end
            endcase
        end
    end

    // 时序逻辑：状态转移和寄存器更新
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_state <= IDLE;
            reg_shift <= 8'd0;
            reg_bit_cnt <= 4'd0;
            reg_sda_prev <= 1'b1;
            reg_scl_prev <= 1'b0;
            reg_is_write <= 1'b0;
            reg_ack <= 1'b1;
            reg_reg_ptr <= 4'd0;
            sda_out <= 1'b1;
            sda_oe <= 1'b0;
            data_ready <= 1'b0;
            addr_match <= 1'b0;
        end else begin
            reg_state <= wire_next_state;
            reg_shift <= wire_next_shift;
            reg_bit_cnt <= wire_next_bit_cnt;
            reg_sda_prev <= sda_in;
            reg_scl_prev <= scl;
            reg_is_write <= wire_is_write;
            reg_ack <= wire_next_ack;
            reg_reg_ptr <= wire_next_reg_ptr;

            // 调试输出
            debug_state <= reg_state;
            debug_bit_cnt <= reg_bit_cnt;

            // 数据写入寄存器
            if (wire_next_state == ACK && reg_state == DATA_RX && reg_bit_cnt == 7)
                reg_registers[reg_reg_ptr] <= wire_next_shift;

            // SDA输出控制
            if (reg_state == ACK && reg_bit_cnt == 0) begin
                sda_out <= reg_ack;
                sda_oe <= 1'b1;
            end else begin
                sda_out <= 1'b1;
                sda_oe <= 1'b0;
            end

            // 数据就绪信号
            if (wire_next_state == ACK && reg_state == DATA_RX && reg_bit_cnt == 7) begin
                data_out <= wire_next_shift;
                data_ready <= 1'b1;
            end else begin
                data_ready <= 1'b0;
            end

            // 地址匹配信号
            if (wire_next_state == ACK && reg_state == ADDR) begin
                addr_match <= 1'b1;
            end else begin
                addr_match <= 1'b0;
            end
        end
    end

endmodule
