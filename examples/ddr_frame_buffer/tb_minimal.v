// tb_minimal.v - Minimal testbench for frame_writer
// Pure Verilog-2001, no SystemVerilog features

`timescale 1ns/1ps

module tb_minimal;

    parameter CLK_PERIOD = 10;
    parameter DATA_WIDTH = 8;
    parameter ADDR_WIDTH = 32;
    parameter PAGE_ID_WIDTH = 7;

    reg clk;
    reg rst_n;
    reg data_valid;
    reg [DATA_WIDTH-1:0] data_in;

    wire ddr_write_en;
    wire [ADDR_WIDTH-1:0] ddr_write_addr;
    wire [DATA_WIDTH-1:0] ddr_write_data;

    wire allocate_req;
    wire complete_write;
    wire [PAGE_ID_WIDTH-1:0] write_page_id;
    wire frame_complete;
    wire [PAGE_ID_WIDTH-1:0] frame_page_id;
    wire [15:0] frame_id;

    // Simple page manager stub
    reg [PAGE_ID_WIDTH-1:0] allocated_page;
    reg allocate_ok;
    reg [1:0] pm_state;
    reg [PAGE_ID_WIDTH-1:0] pm_next;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            allocated_page <= 0;
            allocate_ok <= 0;
            pm_state <= 0;
            pm_next <= 0;
        end else begin
            if (allocate_req) begin
                allocate_ok <= 1;
                allocated_page <= pm_next;
                pm_state <= 1;
                pm_next <= pm_next + 1;
            end else begin
                allocate_ok <= 0;
            end
            if (complete_write) begin
                pm_state <= 2;
            end
        end
    end

    frame_writer #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH)
    ) u_fw (
        .clk(clk),
        .rst_n(rst_n),
        .data_valid(data_valid),
        .data_in(data_in),
        .ddr_write_en(ddr_write_en),
        .ddr_write_addr(ddr_write_addr),
        .ddr_write_data(ddr_write_data),
        .allocate_req(allocate_req),
        .allocate_ok(allocate_ok),
        .allocated_page(allocated_page),
        .complete_write(complete_write),
        .write_page_id(write_page_id),
        .frame_complete(frame_complete),
        .frame_page_id(frame_page_id),
        .frame_id(frame_id)
    );

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

    // Stimulus - send header + 4 data + trailer (20 bytes total)
    initial begin
        wait(rst_n);
        #(CLK_PERIOD * 5);

        data_valid = 0;
        data_in = 0;

        // Frame header: 22 DD 11 EE 5A 5A 5A 5A (8 bytes)
        @(posedge clk); data_valid = 1; data_in = 8'h22;
        @(posedge clk); data_valid = 1; data_in = 8'hDD;
        @(posedge clk); data_valid = 1; data_in = 8'h11;
        @(posedge clk); data_valid = 1; data_in = 8'hEE;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;

        // 4 data bytes
        @(posedge clk); data_valid = 1; data_in = 8'hAA;
        @(posedge clk); data_valid = 1; data_in = 8'hBB;
        @(posedge clk); data_valid = 1; data_in = 8'hCC;
        @(posedge clk); data_valid = 1; data_in = 8'hDD;

        // Frame trailer: 23 DD 11 EE 5A 5A 5A 5A (8 bytes)
        @(posedge clk); data_valid = 1; data_in = 8'h23;
        @(posedge clk); data_valid = 1; data_in = 8'hDD;
        @(posedge clk); data_valid = 1; data_in = 8'h11;
        @(posedge clk); data_valid = 1; data_in = 8'hEE;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;

        // Deassert
        @(posedge clk); data_valid = 0;
    end

    // Monitor
    initial begin
        $timeformat(-9, 0, " ns", 9);
        $display("tb_minimal: Starting");

        wait(frame_complete);
        @(posedge clk);

        $display("Frame complete!");
        $display("  page_id=%0d frame_id=%0d", frame_page_id, frame_id);
        $display("  pm_state=%0d", pm_state);

        if (pm_state == 2) begin
            $display("PASS");
        end else begin
            $display("FAIL: pm_state=%0d expected 2", pm_state);
        end

        $finish;
    end

    // Timeout
    initial begin
        #(CLK_PERIOD * 5000);
        $display("TIMEOUT");
        $finish;
    end

endmodule