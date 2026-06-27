// UART Transceiver - Verilog RTL
//
// 标准 UART 收发器，支持 8N1 帧格式
// 1起始位 + 8数据位(LSB first) + 1停止位
//
// 发送器：并行输入 → 串行输出
// 接收器：串行输入 → 并行输出，中间采样策略

module uart_transceiver #(
    parameter BAUD_DIVIDER = 16  // 系统时钟 / 波特率
)(
    input  wire                    clk,
    input  wire                    rst_n,
    
    // 发送器接口
    input  wire                    tx_start,      // 发送启动信号
    input  wire  [7:0]             tx_data_in,    // 发送数据
    output reg                     tx_busy,       // 发送中
    output reg                     tx_done,       // 发送完成
    output reg                     tx_out,        // TX 输出
    
    // 接收器接口
    input  wire                    rx_in,         // RX 输入
    output reg                     rx_done,       // 接收完成
    output reg  [7:0]              rx_data,       // 接收数据
    output reg                     rx_frame_err,  // 帧错误
    
    // 调试输出
    output reg [1:0]               debug_tx_state,
    output reg [1:0]               debug_rx_state,
    output reg [3:0]               debug_rx_bit
);

    // 状态编码
    localparam TX_IDLE = 1'b0;
    localparam TX_SEND = 1'b1;
    
    localparam RX_IDLE = 1'b0;
    localparam RX_RECV = 1'b1;

    // ========== 发送器 ==========
    
    // 寄存器
    reg [1:0]          reg_tx_state;
    reg [9:0]          reg_tx_shift;     // 10位：停止位|8数据|起始位
    reg [3:0]          reg_tx_bit_cnt;   // 当前位索引 0-9
    reg [4:0]          reg_tx_baud_cnt;  // 波特率计数器
    
    // 组合逻辑
    reg [1:0]          wire_tx_next_state;
    reg [9:0]          wire_tx_next_shift;
    reg [3:0]          wire_tx_next_bit_cnt;
    reg [4:0]          wire_tx_next_baud_cnt;
    reg                wire_tx_next_out;
    reg                wire_tx_next_busy;
    reg                wire_tx_next_done;
    
    // 波特率分频
    wire               tx_baud_tick;
    assign tx_baud_tick = (reg_tx_baud_cnt == BAUD_DIVIDER - 1);
    
    // 组合逻辑：发送器状态机
    always @(*) begin
        wire_tx_next_state = reg_tx_state;
        wire_tx_next_shift = reg_tx_shift;
        wire_tx_next_bit_cnt = reg_tx_bit_cnt;
        wire_tx_next_baud_cnt = reg_tx_baud_cnt;
        wire_tx_next_out = tx_out;
        wire_tx_next_busy = tx_busy;
        wire_tx_next_done = 1'b0;
        
        if (!rst_n) begin
            wire_tx_next_state = TX_IDLE;
            wire_tx_next_out = 1'b1;
            wire_tx_next_busy = 1'b0;
        end else if (tx_start && !tx_busy) begin
            // 启动发送：加载数据
            wire_tx_next_state = TX_SEND;
            wire_tx_next_shift = {1'b1, tx_data_in, 1'b0};  // 停止|数据|起始
            wire_tx_next_bit_cnt = 4'd0;
            wire_tx_next_baud_cnt = 5'd0;
            wire_tx_next_out = 1'b0;  // 起始位
            wire_tx_next_busy = 1'b1;
            wire_tx_next_done = 1'b0;
        end else if (tx_busy && reg_tx_state == TX_SEND) begin
            if (tx_baud_tick) begin
                wire_tx_next_baud_cnt = 5'd0;
                wire_tx_next_bit_cnt = reg_tx_bit_cnt + 1'd1;
                
                if (reg_tx_bit_cnt < 9) begin
                    // 输出下一位
                    wire_tx_next_out = reg_tx_shift[reg_tx_bit_cnt + 1];
                end else begin
                    // 发送完成
                    wire_tx_next_state = TX_IDLE;
                    wire_tx_next_out = 1'b1;
                    wire_tx_next_busy = 1'b0;
                    wire_tx_next_done = 1'b1;
                end
            end else begin
                wire_tx_next_baud_cnt = reg_tx_baud_cnt + 1'd1;
            end
        end
    end
    
    // 时序逻辑：发送器
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_tx_state <= TX_IDLE;
            reg_tx_shift <= 10'd0;
            reg_tx_bit_cnt <= 4'd0;
            reg_tx_baud_cnt <= 5'd0;
            tx_out <= 1'b1;
            tx_busy <= 1'b0;
            tx_done <= 1'b0;
        end else begin
            reg_tx_state <= wire_tx_next_state;
            reg_tx_shift <= wire_tx_next_shift;
            reg_tx_bit_cnt <= wire_tx_next_bit_cnt;
            reg_tx_baud_cnt <= wire_tx_next_baud_cnt;
            tx_out <= wire_tx_next_out;
            tx_busy <= wire_tx_next_busy;
            tx_done <= wire_tx_next_done;
            
            debug_tx_state <= reg_tx_state;
        end
    end

    // ========== 接收器 ==========
    
    // 寄存器
    reg [1:0]          reg_rx_state;
    reg [7:0]          reg_rx_shift;     // 接收移位寄存器
    reg [3:0]          reg_rx_bit_index; // 当前位索引 0-9
    reg [4:0]          reg_rx_baud_cnt;  // 波特率计数器
    reg                reg_rx_prev;      // 上一拍 RX 输入
    
    // 组合逻辑
    reg [1:0]          wire_rx_next_state;
    reg [7:0]          wire_rx_next_shift;
    reg [3:0]          wire_rx_next_bit_index;
    reg [4:0]          wire_rx_next_baud_cnt;
    reg                wire_rx_next_prev;
    reg                wire_rx_next_done;
    reg                wire_rx_next_frame_err;
    reg [7:0]          wire_rx_next_data;
    
    // 采样点检测
    wire               rx_sample_tick;
    assign rx_sample_tick = (reg_rx_baud_cnt == (BAUD_DIVIDER >> 1) - 1);
    
    // 波特率周期结束
    wire               rx_baud_tick;
    assign rx_baud_tick = (reg_rx_baud_cnt == BAUD_DIVIDER - 1);
    
    // 起始位下降沿检测
    wire               rx_start_edge;
    assign rx_start_edge = reg_rx_prev && !rx_in;
    
    // 组合逻辑：接收器状态机
    always @(*) begin
        wire_rx_next_state = reg_rx_state;
        wire_rx_next_shift = reg_rx_shift;
        wire_rx_next_bit_index = reg_rx_bit_index;
        wire_rx_next_baud_cnt = reg_rx_baud_cnt;
        wire_rx_next_prev = reg_rx_prev;
        wire_rx_next_done = 1'b0;
        wire_rx_next_frame_err = rx_frame_err;
        wire_rx_next_data = rx_data;
        
        if (!rst_n) begin
            wire_rx_next_state = RX_IDLE;
        end else if (reg_rx_state == RX_IDLE) begin
            wire_rx_next_prev = rx_in;
            if (rx_start_edge) begin
                // 检测到起始位下降沿
                wire_rx_next_state = RX_RECV;
                wire_rx_next_bit_index = 4'd0;
                wire_rx_next_baud_cnt = 5'd0;
                wire_rx_next_shift = 8'd0;
                wire_rx_next_done = 1'b0;
                wire_rx_next_frame_err = 1'b0;
            end
        end else if (reg_rx_state == RX_RECV) begin
            wire_rx_next_prev = rx_in;
            
            if (rx_baud_tick) begin
                // 波特率周期结束，进入下一位
                wire_rx_next_baud_cnt = 5'd0;
                wire_rx_next_bit_index = reg_rx_bit_index + 1'd1;
            end else begin
                wire_rx_next_baud_cnt = reg_rx_baud_cnt + 1'd1;
            end
            
            // 在每位中间采样
            if (rx_sample_tick) begin
                if (reg_rx_bit_index >= 1 && reg_rx_bit_index <= 8) begin
                    // 数据位采样，LSB first
                    wire_rx_next_shift = {rx_in, reg_rx_shift[7:1]};
                end else if (reg_rx_bit_index == 9) begin
                    // 停止位采样
                    if (!rx_in) begin
                        wire_rx_next_frame_err = 1'b1;
                    end
                end
            end
            
            // 停止位结束后
            if (reg_rx_bit_index == 9 && rx_baud_tick) begin
                wire_rx_next_state = RX_IDLE;
                wire_rx_next_data = wire_rx_next_shift;
                wire_rx_next_done = 1'b1;
            end
        end
    end
    
    // 时序逻辑：接收器
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_rx_state <= RX_IDLE;
            reg_rx_shift <= 8'd0;
            reg_rx_bit_index <= 4'd0;
            reg_rx_baud_cnt <= 5'd0;
            reg_rx_prev <= 1'b1;
            rx_data <= 8'd0;
            rx_done <= 1'b0;
            rx_frame_err <= 1'b0;
        end else begin
            reg_rx_state <= wire_rx_next_state;
            reg_rx_shift <= wire_rx_next_shift;
            reg_rx_bit_index <= wire_rx_next_bit_index;
            reg_rx_baud_cnt <= wire_rx_next_baud_cnt;
            reg_rx_prev <= wire_rx_next_prev;
            rx_data <= wire_rx_next_data;
            rx_done <= wire_rx_next_done;
            rx_frame_err <= wire_rx_next_frame_err;
            
            debug_rx_state <= reg_rx_state;
            debug_rx_bit <= reg_rx_bit_index;
        end
    end

endmodule
