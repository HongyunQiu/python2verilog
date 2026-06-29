// top.v - DDR Frame Buffer & Retransmit Manager 顶层模块
// Cyclone10 + DDR4 Memory Interface IP
// 参数化设计：支持 mini/test/full 三种配置

module top #(
    // === 帧参数 ===
    parameter FRAME_WIDTH     = 128,
    parameter FRAME_HEIGHT    = 128,
    parameter PIXEL_BITS      = 16,
    parameter PIXEL_BYTES     = 2,
    parameter FRAME_DATA_SIZE = 32768,
    parameter FRAME_TOTAL_SIZE = 32784,
    
    // === DDR 参数 ===
    parameter PAGE_SIZE       = 65536,
    parameter NUM_PAGES       = 16,
    parameter DDR_CAPACITY    = 1048576,
    
    // === 位宽参数 ===
    parameter PAGE_ID_WIDTH   = 4,
    parameter ADDR_WIDTH      = 20,
    parameter FRAME_OFFSET_WIDTH = 16,
    parameter PKT_INDEX_WIDTH = 4,
    parameter FRAME_ID_WIDTH  = 16,
    
    // === 包参数（固定） ===
    parameter PACKET_PAYLOAD_SIZE = 4096,
    parameter PACKET_HEADER_SIZE  = 12,
    parameter PACKET_CRC_SIZE     = 4,
    parameter PACKETS_PER_FRAME   = 9,
    
    // === 数据总线宽度 ===
    parameter DATA_WIDTH      = 8,
    
    // === 帧头帧尾（固定） ===
    parameter [63:0] FRAME_HEADER  = 64'h5A5A5A5AEE11DD22,
    parameter [63:0] FRAME_TRAILER = 64'h5A5A5A5AEE11DD23
)(
    input        clk,
    input        rst_n,
    
    // 摄像头数据输入
    input        cam_data_valid,
    input [DATA_WIDTH-1:0] cam_data,
    
    // DDR4 接口（Avalon-ST）
    output reg   ddr_write_en,
    output reg [ADDR_WIDTH-1:0] ddr_write_addr,
    output reg [DATA_WIDTH-1:0] ddr_write_data,
    
    output reg   ddr_read_req,
    output reg [ADDR_WIDTH-1:0] ddr_read_addr,
    input [DATA_WIDTH-1:0] ddr_read_data,
    input        ddr_read_valid,
    
    // 网络输出
    output reg   net_data_valid,
    output reg [DATA_WIDTH-1:0] net_data,
    output reg   net_last,
    output reg   net_is_retransmit,
    
    // Avalon-MM 控制接口
    input [7:0]  avm_address,
    input        avm_read,
    input        avm_write,
    input [31:0] avm_writedata,
    output wire [31:0] avm_readdata,
    output wire   avm_readdatavalid,
    output wire   avm_waitrequest
);

    // 页管理器信号
    wire        allocate_ok;
    wire [PAGE_ID_WIDTH-1:0] allocated_page;
    wire        allocate_req;
    wire        complete_write;
    wire [PAGE_ID_WIDTH-1:0] write_page_id;
    wire        start_read_req;
    wire [PAGE_ID_WIDTH-1:0] read_page_id;
    wire        complete_read;
    wire [PAGE_ID_WIDTH-1:0] read_done_page_id;
    wire [15:0] frame_counter;
    wire [1:0]  status_page_state;
    wire [15:0] status_frame_id;
    
    // 帧写入器信号
    wire        frame_complete;
    wire [PAGE_ID_WIDTH-1:0] frame_page_id;
    wire [15:0] frame_id;
    wire        fw_ddr_write_en;
    wire [ADDR_WIDTH-1:0] fw_ddr_write_addr;
    wire [DATA_WIDTH-1:0] fw_ddr_write_data;
    
    // 帧读取器信号
    wire        fr_data_valid;
    wire [DATA_WIDTH-1:0] fr_data;
    wire        fr_data_last;
    wire        fr_read_complete;
    wire        fr_ddr_read_req;
    wire [ADDR_WIDTH-1:0] fr_ddr_read_addr;
    
    // 仲裁器信号
    wire        arb_data_valid;
    wire [DATA_WIDTH-1:0] arb_data;
    wire        arb_data_last;
    wire        arb_is_retransmit;
    
    // 控制接口信号
    wire        retransmit_req;
    wire [PAGE_ID_WIDTH-1:0] retransmit_page_id;
    wire [15:0] retransmit_start_pkt;
    wire [15:0] retransmit_num_pkts;
    
    // 实例化页管理器
    page_manager #(
        .NUM_PAGES(NUM_PAGES),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH)
    ) u_page_manager (
        .clk(clk),
        .rst_n(rst_n),
        .allocate_req(allocate_req),
        .allocate_ok(allocate_ok),
        .allocated_page(allocated_page),
        .complete_write(complete_write),
        .write_page_id(write_page_id),
        .start_read(start_read_req),
        .read_page_id(read_page_id),
        .complete_read(complete_read),
        .read_done_page_id(read_done_page_id),
        .status_req(1'b0),
        .status_page_id({PAGE_ID_WIDTH{1'b0}}),
        .status_page_state(status_page_state),
        .status_frame_id(status_frame_id),
        .frame_counter(frame_counter)
    );
    
    // 实例化帧写入器
    frame_writer #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH)
    ) u_frame_writer (
        .clk(clk),
        .rst_n(rst_n),
        .data_valid(cam_data_valid),
        .data_in(cam_data),
        .ddr_write_en(fw_ddr_write_en),
        .ddr_write_addr(fw_ddr_write_addr),
        .ddr_write_data(fw_ddr_write_data),
        .allocate_req(allocate_req),
        .allocate_ok(allocate_ok),
        .allocated_page(allocated_page),
        .complete_write(complete_write),
        .write_page_id(write_page_id),
        .frame_complete(frame_complete),
        .frame_page_id(frame_page_id),
        .frame_id(frame_id)
    );
    
    // 实例化帧读取器
    frame_reader #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH)
    ) u_frame_reader (
        .clk(clk),
        .rst_n(rst_n),
        .start_read(retransmit_req),
        .page_id_in(retransmit_page_id),
        .ddr_read_req(fr_ddr_read_req),
        .ddr_read_addr(fr_ddr_read_addr),
        .ddr_read_data(ddr_read_data),
        .ddr_read_valid(ddr_read_valid),
        .start_read_req(start_read_req),
        .read_page_id(read_page_id),
        .complete_read(complete_read),
        .read_done_page_id(read_done_page_id),
        .data_valid(fr_data_valid),
        .data_out(fr_data),
        .data_last(fr_data_last),
        .read_complete(fr_read_complete)
    );
    
    // 实例化输出仲裁器
    output_arbiter #(
        .DATA_WIDTH(DATA_WIDTH)
    ) u_output_arbiter (
        .clk(clk),
        .rst_n(rst_n),
        .realtime_data_valid(cam_data_valid),
        .realtime_data(cam_data),
        .realtime_last(1'b0),
        .retransmit_data_valid(fr_data_valid),
        .retransmit_data(fr_data),
        .retransmit_last(fr_data_last),
        .retransmit_start(retransmit_req),
        .data_valid(arb_data_valid),
        .data_out(arb_data),
        .data_last(arb_data_last),
        .is_retransmit(arb_is_retransmit)
    );
    
    // 实例化控制接口
    command_interface #(
        .ADDR_WIDTH(8),
        .DATA_WIDTH(32),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH)
    ) u_command_interface (
        .clk(clk),
        .rst_n(rst_n),
        .avm_address(avm_address),
        .avm_read(avm_read),
        .avm_write(avm_write),
        .avm_writedata(avm_writedata),
        .avm_readdata(avm_readdata),
        .avm_readdatavalid(avm_readdatavalid),
        .avm_waitrequest(avm_waitrequest),
        .retransmit_req(retransmit_req),
        .retransmit_page_id(retransmit_page_id),
        .retransmit_start_pkt(retransmit_start_pkt),
        .retransmit_num_pkts(retransmit_num_pkts),
        .frame_counter(frame_counter),
        .next_write_page({PAGE_ID_WIDTH{1'b0}})
    );
    
    // DDR 写接口
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ddr_write_en <= 0;
            ddr_write_addr <= 0;
            ddr_write_data <= 0;
        end else begin
            ddr_write_en <= fw_ddr_write_en;
            ddr_write_addr <= fw_ddr_write_addr;
            ddr_write_data <= fw_ddr_write_data;
        end
    end
    
    // DDR 读接口
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ddr_read_req <= 0;
            ddr_read_addr <= 0;
        end else begin
            ddr_read_req <= fr_ddr_read_req;
            ddr_read_addr <= fr_ddr_read_addr;
        end
    end
    
    // 网络输出
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            net_data_valid <= 0;
            net_data <= 0;
            net_last <= 0;
            net_is_retransmit <= 0;
        end else begin
            net_data_valid <= arb_data_valid;
            net_data <= arb_data;
            net_last <= arb_data_last;
            net_is_retransmit <= arb_is_retransmit;
        end
    end

endmodule
