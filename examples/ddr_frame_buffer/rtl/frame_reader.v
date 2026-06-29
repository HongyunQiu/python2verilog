// frame_reader.v - 帧读取器
// 从 DDR 读取指定页的帧数据，用于重发

module frame_reader #(
    parameter DATA_WIDTH       = 8,
    parameter ADDR_WIDTH       = 20,
    parameter PAGE_ID_WIDTH    = 4,
    parameter PAGE_SIZE        = 65536,
    parameter [63:0] FRAME_TRAILER = 64'h5A5A5A5AEE11DD23
)(
    input        clk,
    input        rst_n,
    
    // 控制接口
    input        start_read,
    input [PAGE_ID_WIDTH-1:0] page_id_in,
    
    // DDR 读接口
    output reg   ddr_read_req,
    output reg [ADDR_WIDTH-1:0] ddr_read_addr,
    input [DATA_WIDTH-1:0] ddr_read_data,
    input        ddr_read_valid,
    
    // 页管理器接口
    output reg   start_read_req,
    output reg [PAGE_ID_WIDTH-1:0] read_page_id,
    output reg   complete_read,
    output reg [PAGE_ID_WIDTH-1:0] read_done_page_id,
    
    // 输出数据
    output reg   data_valid,
    output reg [DATA_WIDTH-1:0] data_out,
    output reg   data_last,
    output reg   read_complete
);

    // 状态机
    localparam IDLE     = 2'b00;
    localparam READING  = 2'b01;
    
    reg [1:0] state;
    reg [PAGE_ID_WIDTH-1:0] current_page;
    reg [ADDR_WIDTH-1:0] read_addr;
    
    // 帧尾检测移位寄存器
    reg [63:0] shift_reg;
    reg [6:0] shift_count;
    
    wire [63:0] trailer_le = 64'h23DD11EE5A5A5A5A;
    wire trailer_match = (shift_reg == trailer_le);
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            current_page <= 0;
            read_addr <= 0;
            shift_reg <= 0;
            shift_count <= 0;
            ddr_read_req <= 0;
            start_read_req <= 0;
            complete_read <= 0;
            data_valid <= 0;
            data_last <= 0;
            read_complete <= 0;
        end else begin
            start_read_req <= 0;
            complete_read <= 0;
            data_valid <= 0;
            data_last <= 0;
            read_complete <= 0;
            ddr_read_req <= 0;
            
            case (state)
                IDLE:
                    if (start_read) begin
                        start_read_req <= 1;
                        read_page_id <= page_id_in;
                        current_page <= page_id_in;
                        read_addr <= page_id_in * PAGE_SIZE;
                        shift_reg <= 0;
                        shift_count <= 0;
                        state <= READING;
                        ddr_read_req <= 1;
                        ddr_read_addr <= read_addr;
                    end
                    
                READING:
                    if (ddr_read_valid) begin
                        data_valid <= 1;
                        data_out <= ddr_read_data;
                        
                        // 更新移位寄存器
                        shift_reg <= (shift_reg << 8) | ddr_read_data;
                        shift_count <= shift_count + 1;
                        
                        // 检测帧尾
                        if (shift_count >= 8 && trailer_match) begin
                            data_last <= 1;
                            read_complete <= 1;
                            complete_read <= 1;
                            read_done_page_id <= current_page;
                            state <= IDLE;
                            ddr_read_req <= 0;
                        end else begin
                            read_addr <= read_addr + 1;
                            ddr_read_addr <= read_addr;
                        end
                    end
            endcase
        end
    end

endmodule
