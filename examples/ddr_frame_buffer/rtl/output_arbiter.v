// output_arbiter.v - 输出仲裁器
// 仲裁实时流和重发流，重发插队，实时流继续但延迟

module output_arbiter #(
    parameter DATA_WIDTH    = 8,
    parameter PKT_SIZE      = 4112,  // 包大小
    parameter PKT_FIFO_DEPTH = 64
)(
    input        clk,
    input        rst_n,
    
    // 实时数据输入
    input        realtime_data_valid,
    input [DATA_WIDTH-1:0] realtime_data,
    input        realtime_last,  // 包结束
    
    // 重发数据输入
    input        retransmit_data_valid,
    input [DATA_WIDTH-1:0] retransmit_data,
    input        retransmit_last,
    input        retransmit_start,  // 开始重发
    
    // 输出数据
    output reg   data_valid,
    output reg [DATA_WIDTH-1:0] data_out,
    output reg   data_last,
    output reg   is_retransmit  // 标记是否为重发包
);

    // 状态机
    localparam REALTIME   = 1'b0;
    localparam RETRANSMIT = 1'b1;
    
    reg state;
    
    // 实时数据 FIFO（简化版）
    reg [DATA_WIDTH-1:0] realtime_fifo [0:PKT_FIFO_DEPTH-1];
    reg [7:0] realtime_fifo_wr;
    reg [7:0] realtime_fifo_rd;
    reg realtime_fifo_empty;
    
    // 重发数据 FIFO
    reg [DATA_WIDTH-1:0] retransmit_fifo [0:PKT_FIFO_DEPTH-1];
    reg [7:0] retransmit_fifo_wr;
    reg [7:0] retransmit_fifo_rd;
    reg retransmit_fifo_empty;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= REALTIME;
            data_valid <= 0;
            data_last <= 0;
            is_retransmit <= 0;
            realtime_fifo_empty <= 1;
            retransmit_fifo_empty <= 1;
        end else begin
            data_valid <= 0;
            data_last <= 0;
            
            // 写入 FIFO
            if (realtime_data_valid && realtime_fifo_empty) begin
                realtime_fifo[realtime_fifo_wr] <= realtime_data;
                realtime_fifo_wr <= realtime_fifo_wr + 1;
                realtime_fifo_empty <= 0;
                if (realtime_last) begin
                    // 标记包结束
                end
            end
            
            if (retransmit_data_valid && retransmit_fifo_empty) begin
                retransmit_fifo[retransmit_fifo_wr] <= retransmit_data;
                retransmit_fifo_wr <= retransmit_fifo_wr + 1;
                retransmit_fifo_empty <= 0;
                if (retransmit_last) begin
                    // 标记包结束
                end
            end
            
            // 仲裁逻辑
            if (retransmit_start) begin
                state <= RETRANSMIT;
            end
            
            case (state)
                REALTIME:
                    if (!realtime_fifo_empty) begin
                        data_valid <= 1;
                        data_out <= realtime_fifo[realtime_fifo_rd];
                        realtime_fifo_rd <= realtime_fifo_rd + 1;
                        is_retransmit <= 0;
                    end
                    
                RETRANSMIT:
                    if (!retransmit_fifo_empty) begin
                        data_valid <= 1;
                        data_out <= retransmit_fifo[retransmit_fifo_rd];
                        retransmit_fifo_rd <= retransmit_fifo_rd + 1;
                        is_retransmit <= 1;
                        if (retransmit_last) begin
                            state <= REALTIME;  // 重发完成，恢复实时流
                        end
                    end else if (!realtime_fifo_empty) begin
                        // 重发 FIFO 空，发送实时数据
                        data_valid <= 1;
                        data_out <= realtime_fifo[realtime_fifo_rd];
                        realtime_fifo_rd <= realtime_fifo_rd + 1;
                        is_retransmit <= 0;
                    end
            endcase
        end
    end

endmodule
