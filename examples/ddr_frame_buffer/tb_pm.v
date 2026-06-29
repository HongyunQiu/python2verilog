// tb_pm.v - Minimal testbench for page_manager
`timescale 1ns/1ps

module tb_pm;

    parameter CLK_PERIOD = 10;
    parameter NUM_PAGES = 50;
    parameter PAGE_ID_WIDTH = 7;

    reg clk;
    reg rst_n;
    reg allocate_req;
    reg complete_write;
    reg [PAGE_ID_WIDTH-1:0] write_page_id;
    reg start_read;
    reg [PAGE_ID_WIDTH-1:0] read_page_id;
    reg complete_read;
    reg [PAGE_ID_WIDTH-1:0] read_done_page_id;
    reg status_req;
    reg [PAGE_ID_WIDTH-1:0] status_page_id;

    wire allocate_ok;
    wire [PAGE_ID_WIDTH-1:0] allocated_page;
    wire [1:0] status_page_state;
    wire [15:0] status_frame_id;
    wire [15:0] frame_counter;

    page_manager #(
        .NUM_PAGES(NUM_PAGES),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH)
    ) u_pm (
        .clk(clk),
        .rst_n(rst_n),
        .allocate_req(allocate_req),
        .allocate_ok(allocate_ok),
        .allocated_page(allocated_page),
        .complete_write(complete_write),
        .write_page_id(write_page_id),
        .start_read(start_read),
        .read_page_id(read_page_id),
        .complete_read(complete_read),
        .read_done_page_id(read_done_page_id),
        .status_req(status_req),
        .status_page_id(status_page_id),
        .status_page_state(status_page_state),
        .status_frame_id(status_frame_id),
        .frame_counter(frame_counter)
    );

    // VCD dump
    initial begin
        $dumpfile("tb_pm.vcd");
        $dumpvars(0, tb_pm);
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

        // 初始化所有信号
        allocate_req = 0;
        write_page_id = 0;
        complete_write = 0;
        start_read = 0;
        read_page_id = 0;
        complete_read = 0;
        read_done_page_id = 0;
        status_req = 0;
        status_page_id = 0;

        // Test 1: Allocate page 0
        allocate_req = 1;
        @(posedge clk);  // 时钟沿1: allocate_req=1, 触发分配
        allocate_req = 0;
        @(posedge clk);  // 时钟沿2: allocate_ok=1, allocated_page=0

        $display("Test 1: Allocate");
        $display("  allocate_ok=%0d allocated_page=%0d", allocate_ok, allocated_page);
        if (allocated_page == 0) begin
            $display("  PASS: Page 0 allocated");
        end else begin
            $display("  FAIL");
        end

        // Test 2: Complete write on page 0
        @(posedge clk);  // 时钟沿3: 空闲
        complete_write = 1;
        write_page_id = 0;
        @(posedge clk);  // 时钟沿4: complete_write=1, page_state_0 <= READY
        complete_write = 0;
        @(posedge clk);  // 时钟沿5: page_state_0 已经是 READY

        // 查询状态（需要额外周期让状态传播到输出）
        status_req = 1;
        status_page_id = 0;
        @(posedge clk);  // 时钟沿6: status_page_state <= page_state_0 (=READY)
        status_req = 0;
        @(posedge clk);  // 时钟沿7: status_page_state 已经是 READY

        $display("Test 2: Complete write");
        $display("  status_page_state=%0d (expected 2=READY)", status_page_state);
        if (status_page_state == 2) begin
            $display("  PASS: Page 0 is READY");
        end else begin
            $display("  FAIL");
        end

        // Test 3: Allocate page 1
        @(posedge clk);  // 时钟沿8: 空闲
        allocate_req = 1;
        @(posedge clk);  // 时钟沿9: allocate_req=1, 触发分配
        allocate_req = 0;
        @(posedge clk);  // 时钟沿10: allocate_ok=1, allocated_page=1

        $display("Test 3: Allocate page 1");
        $display("  allocate_ok=%0d allocated_page=%0d frame_counter=%0d",
                 allocate_ok, allocated_page, frame_counter);
        if (allocated_page == 1) begin
            $display("  PASS");
        end else begin
            $display("  FAIL: expected page 1, got %0d", allocated_page);
        end

        // Test 4: Start read on page 0
        @(posedge clk);  // 时钟沿11: 空闲
        start_read = 1;
        read_page_id = 0;
        @(posedge clk);  // 时钟沿12: start_read=1, page_state_0 <= READING
        start_read = 0;
        @(posedge clk);  // 时钟沿13: page_state_0 已经是 READING

        // 查询状态
        status_req = 1;
        status_page_id = 0;
        @(posedge clk);  // 时钟沿14: status_page_state <= page_state_0 (=READING)
        status_req = 0;
        @(posedge clk);  // 时钟沿15: status_page_state 已经是 READING

        $display("Test 4: Start read");
        $display("  status_page_state=%0d (expected 3=READING)", status_page_state);
        if (status_page_state == 3) begin
            $display("  PASS: Page 0 is READING");
        end else begin
            $display("  FAIL");
        end

        // Test 5: Complete read on page 0
        @(posedge clk);  // 时钟沿16: 空闲
        complete_read = 1;
        read_done_page_id = 0;
        @(posedge clk);  // 时钟沿17: complete_read=1, page_state_0 <= READY
        complete_read = 0;
        @(posedge clk);  // 时钟沿18: page_state_0 已经是 READY

        // 查询状态
        status_req = 1;
        status_page_id = 0;
        @(posedge clk);  // 时钟沿19: status_page_state <= page_state_0 (=READY)
        status_req = 0;
        @(posedge clk);  // 时钟沿20: status_page_state 已经是 READY

        $display("Test 5: Complete read");
        $display("  status_page_state=%0d (expected 2=READY)", status_page_state);
        if (status_page_state == 2) begin
            $display("  PASS: Page 0 is READY again");
        end else begin
            $display("  FAIL");
        end

        $display("\n=== All tests done ===");
        $finish;
    end

    // Timeout
    initial begin
        #(CLK_PERIOD * 1000);
        $display("TIMEOUT");
        $finish;
    end

endmodule
