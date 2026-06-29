// tb_system.v - 系统级测试平台
`timescale 1ns/1ps

module tb_system;

    parameter CLK_PERIOD = 10;
    parameter DATA_WIDTH = 8;
    parameter ADDR_WIDTH = 32;
    parameter PAGE_ID_WIDTH = 7;
    parameter NUM_PAGES = 50;

    reg clk;
    reg rst_n;
    
    reg cam_data_valid;
    reg [DATA_WIDTH-1:0] cam_data;
    
    wire ddr_write_en;
    wire [ADDR_WIDTH-1:0] ddr_write_addr;
    wire [DATA_WIDTH-1:0] ddr_write_data;
    
    wire ddr_read_req;
    wire [ADDR_WIDTH-1:0] ddr_read_addr;
    reg [DATA_WIDTH-1:0] ddr_read_data;
    reg ddr_read_valid;
    
    wire net_data_valid;
    wire [DATA_WIDTH-1:0] net_data;
    wire net_last;
    wire net_is_retransmit;
    
    reg [7:0] avm_address;
    reg avm_read;
    reg avm_write;
    reg [31:0] avm_writedata;
    wire [31:0] avm_readdata;
    wire avm_readdatavalid;
    wire avm_waitrequest;

    top #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH),
        .NUM_PAGES(NUM_PAGES)
    ) u_top (
        .clk(clk),
        .rst_n(rst_n),
        .cam_data_valid(cam_data_valid),
        .cam_data(cam_data),
        .ddr_write_en(ddr_write_en),
        .ddr_write_addr(ddr_write_addr),
        .ddr_write_data(ddr_write_data),
        .ddr_read_req(ddr_read_req),
        .ddr_read_addr(ddr_read_addr),
        .ddr_read_data(ddr_read_data),
        .ddr_read_valid(ddr_read_valid),
        .net_data_valid(net_data_valid),
        .net_data(net_data),
        .net_last(net_last),
        .net_is_retransmit(net_is_retransmit),
        .avm_address(avm_address),
        .avm_read(avm_read),
        .avm_write(avm_write),
        .avm_writedata(avm_writedata),
        .avm_readdata(avm_readdata),
        .avm_readdatavalid(avm_readdatavalid),
        .avm_waitrequest(avm_waitrequest)
    );

    // VCD dump
    initial begin
        $dumpfile("tb_system.vcd");
        $dumpvars(0, tb_system);
    end

    // Clock
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    // Reset
    initial begin
        rst_n = 0;
        #(CLK_PERIOD * 10);
        rst_n = 1;
    end

    // Test sequence
    initial begin
        wait(rst_n);
        #(CLK_PERIOD * 2);
        
        // 初始化
        cam_data_valid = 0;
        cam_data = 0;
        avm_read = 0;
        avm_write = 0;
        avm_writedata = 0;
        avm_address = 0;
        ddr_read_data = 0;
        ddr_read_valid = 0;
        
        // 发送帧头 (0x5A5A5A5AEE11DD22)
        cam_data_valid = 1;
        cam_data = 8'h22; @(posedge clk);
        cam_data = 8'hDD; @(posedge clk);
        cam_data = 8'h11; @(posedge clk);
        cam_data = 8'hEE; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        
        // 帧数据 (100 bytes)
        cam_data = 8'h00; @(posedge clk);
        cam_data = 8'h01; @(posedge clk);
        cam_data = 8'h02; @(posedge clk);
        cam_data = 8'h03; @(posedge clk);
        cam_data = 8'h04; @(posedge clk);
        cam_data = 8'h05; @(posedge clk);
        cam_data = 8'h06; @(posedge clk);
        cam_data = 8'h07; @(posedge clk);
        cam_data = 8'h08; @(posedge clk);
        cam_data = 8'h09; @(posedge clk);
        
        // 帧尾 (0x5A5A5A5AEE11DD23)
        cam_data = 8'h23; @(posedge clk);
        cam_data = 8'hDD; @(posedge clk);
        cam_data = 8'h11; @(posedge clk);
        cam_data = 8'hEE; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        cam_data = 8'h5A; @(posedge clk);
        
        cam_data_valid = 0;
        @(posedge clk);
        
        // 等待帧完成
        repeat (20) @(posedge clk);
        
        $display("=== Test Complete ===");
        $finish;
    end

    // Timeout
    initial begin
        #(CLK_PERIOD * 10000);
        $display("TIMEOUT");
        $finish;
    end

endmodule
