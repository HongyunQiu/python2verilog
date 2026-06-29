// frame_writer.v - 帧写入器
// 接收帧数据字节流，检测帧头帧尾，写入 DDR

module frame_writer #(
    parameter DATA_WIDTH    = 8,
    parameter ADDR_WIDTH    = 32,
    parameter PAGE_ID_WIDTH = 7
)(
    input        clk,
    input        rst_n,
    
    // 输入数据接口
    input        data_valid,
    input [DATA_WIDTH-1:0] data_in,
    
    // DDR 写接口
    output reg   ddr_write_en,
    output reg [ADDR_WIDTH-1:0] ddr_write_addr,
    output reg [DATA_WIDTH-1:0] ddr_write_data,
    
    // 页管理器接口
    output reg   allocate_req,
    input        allocate_ok,
    input [PAGE_ID_WIDTH-1:0] allocated_page,
    
    output reg   complete_write,
    output reg [PAGE_ID_WIDTH-1:0] write_page_id,
    
    // 帧完成信号
    output reg   frame_complete,
    output reg [PAGE_ID_WIDTH-1:0] frame_page_id,
    output reg [15:0] frame_id
);

    // 状态机
    localparam IDLE     = 2'b00;
    localparam IN_FRAME = 2'b01;
    
    reg [1:0] state;
    reg [PAGE_ID_WIDTH-1:0] current_page;
    reg [ADDR_WIDTH-1:0] write_addr;
    
    // 帧头检测移位寄存器（64-bit）
    reg [63:0] shift_reg;
    reg [6:0] shift_count;
    
    // 帧头/帧尾检测
    wire [63:0] header_le = 64'h5A5A5A5AEE11DD22;
    wire [63:0] trailer_le = 64'h5A5A5A5AEE11DD23;
    
    wire header_match = (shift_reg == header_le);
    wire trailer_match = (shift_reg == trailer_le);
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            current_page <= 0;
            write_addr <= 0;
            shift_reg <= 0;
            shift_count <= 0;
            ddr_write_en <= 0;
            allocate_req <= 0;
            complete_write <= 0;
            frame_complete <= 0;
            frame_page_id <= 0;
            frame_id <= 0;
            write_page_id <= 0;
        end else begin
            // 默认值
            ddr_write_en <= 0;
            allocate_req <= 0;
            complete_write <= 0;
            frame_complete <= 0;
            
            if (data_valid) begin
                // 更新移位寄存器
                shift_reg <= (shift_reg << 8) | {{(DATA_WIDTH-8){1'b0}}, data_in};
                shift_count <= shift_count + 1;
                
                case (state)
                    IDLE:
                        if (shift_count >= 8 && header_match) begin
                            // 检测到帧头，请求分配页
                            allocate_req <= 1;
                            if (allocate_ok) begin
                                state <= IN_FRAME;
                                current_page <= allocated_page;
                                write_addr <= allocated_page * 20971520; // PAGE_SIZE = 20MB
                                shift_count <= 0;
                                shift_reg <= 0;
                            end
                        end
                        
                    IN_FRAME:
                        begin
                            // 写入 DDR
                            ddr_write_en <= 1;
                            ddr_write_addr <= write_addr;
                            ddr_write_data <= data_in;
                            write_addr <= write_addr + 1;
                            
                            // 检测帧尾
                            if (shift_count >= 8 && trailer_match) begin
                                // 帧完成
                                complete_write <= 1;
                                write_page_id <= current_page;
                                frame_complete <= 1;
                                frame_page_id <= current_page;
                                frame_id <= current_page;
                                state <= IDLE;
                                shift_count <= 0;
                                shift_reg <= 0;
                            end
                        end
                endcase
            end
        end
    end

endmodule
