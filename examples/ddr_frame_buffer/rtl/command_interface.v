// command_interface.v - 控制接口（Avalon-MM 寄存器映射）
// 接收上位机重发指令

module command_interface #(
    parameter ADDR_WIDTH = 8,
    parameter DATA_WIDTH = 32,
    parameter PAGE_ID_WIDTH = 7
)(
    input        clk,
    input        rst_n,
    
    // Avalon-MM 从接口
    input [ADDR_WIDTH-1:0] avm_address,
    input        avm_read,
    input        avm_write,
    input [DATA_WIDTH-1:0] avm_writedata,
    output reg [DATA_WIDTH-1:0] avm_readdata,
    output reg   avm_readdatavalid,
    output reg   avm_waitrequest,
    
    // 重发控制
    output reg   retransmit_req,
    output reg [PAGE_ID_WIDTH-1:0] retransmit_page_id,
    output reg [15:0] retransmit_start_pkt,
    output reg [15:0] retransmit_num_pkts,
    
    // 状态查询
    input [15:0] frame_counter,
    input [PAGE_ID_WIDTH-1:0] next_write_page
);

    // 寄存器地址映射
    localparam REG_RETRANSMIT_CMD   = 8'h00;  // 重发命令
    localparam REG_RETRANSMIT_PAGE  = 8'h04;  // 重发页号
    localparam REG_RETRANSMIT_START = 8'h08;  // 起始包号
    localparam REG_RETRANSMIT_NUM   = 8'h0C;  // 包数量
    localparam REG_FRAME_COUNTER    = 8'h10;  // 帧计数器
    localparam REG_NEXT_WRITE_PAGE  = 8'h14;  // 下一页号
    localparam REG_PAGE_STATES      = 8'h18;  // 页状态基地址
    
    // 内部寄存器
    reg [31:0] reg_retransmit_cmd;
    reg [PAGE_ID_WIDTH-1:0] reg_retransmit_page;
    reg [15:0] reg_retransmit_start;
    reg [15:0] reg_retransmit_num;
    
    // 写逻辑
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_retransmit_cmd <= 0;
            reg_retransmit_page <= 0;
            reg_retransmit_start <= 0;
            reg_retransmit_num <= 0;
            retransmit_req <= 0;
        end else begin
            if (avm_write && !avm_waitrequest) begin
                case (avm_address)
                    REG_RETRANSMIT_CMD:   reg_retransmit_cmd <= avm_writedata;
                    REG_RETRANSMIT_PAGE:  reg_retransmit_page <= avm_writedata[PAGE_ID_WIDTH-1:0];
                    REG_RETRANSMIT_START: reg_retransmit_start <= avm_writedata[15:0];
                    REG_RETRANSMIT_NUM:   reg_retransmit_num <= avm_writedata[15:0];
                endcase
            end
            
            // 重发命令触发
            if (reg_retransmit_cmd == 32'hDEADBEEF) begin
                retransmit_req <= 1;
                retransmit_page_id <= reg_retransmit_page;
                retransmit_start_pkt <= reg_retransmit_start;
                retransmit_num_pkts <= reg_retransmit_num;
                reg_retransmit_cmd <= 0;  // 清除命令
            end else begin
                retransmit_req <= 0;
            end
        end
    end
    
    // 读逻辑
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            avm_readdata <= 0;
            avm_readdatavalid <= 0;
            avm_waitrequest <= 0;
        end else begin
            avm_readdatavalid <= 0;
            avm_waitrequest <= 0;
            
            if (avm_read && !avm_waitrequest) begin
                case (avm_address)
                    REG_RETRANSMIT_CMD:   avm_readdata <= reg_retransmit_cmd;
                    REG_RETRANSMIT_PAGE:  avm_readdata <= {{(32-PAGE_ID_WIDTH){1'b0}}, reg_retransmit_page};
                    REG_RETRANSMIT_START: avm_readdata <= {{16{1'b0}}, reg_retransmit_start};
                    REG_RETRANSMIT_NUM:   avm_readdata <= {{16{1'b0}}, reg_retransmit_num};
                    REG_FRAME_COUNTER:    avm_readdata <= {{16{1'b0}}, frame_counter};
                    REG_NEXT_WRITE_PAGE:  avm_readdata <= {{(32-PAGE_ID_WIDTH){1'b0}}, next_write_page};
                    default:              avm_readdata <= 0;
                endcase
                avm_readdatavalid <= 1;
            end
        end
    end

endmodule
