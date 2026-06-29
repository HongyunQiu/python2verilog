// tb_ddr_frame_buffer.v - DDR Frame Buffer Testbench
// 使用简化帧（帧头+少量数据+帧尾）验证基本功能

`timescale 1ns/1ps

module tb_ddr_frame_buffer;

    // Parameters
    parameter CLK_PERIOD = 10;  // 100 MHz
    parameter DATA_WIDTH = 8;
    parameter ADDR_WIDTH = 32;
    parameter PAGE_ID_WIDTH = 7;
    parameter NUM_PAGES = 51;
    parameter PAGE_SIZE = 20*1024*1024;  // 20MB
    
    // Simplified frame size for testing (header + 200 bytes + trailer)
    parameter TEST_FRAME_SIZE = 216;
    
    // Frame header/trailer constants
    parameter FRAME_HEADER = 64'h5A5A5A5AEE11DD22;
    parameter FRAME_TRAILER = 64'h5A5A5A5AEE11DD23;
    
    // Clock and reset
    reg clk;
    reg rst_n;
    
    // Generate clock
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end
    
    // Reset sequence
    initial begin
        rst_n = 0;
        #(CLK_PERIOD * 10);
        rst_n = 1;
    end
    
    // Test frame data (simplified: header + pattern + trailer)
    reg [7:0] test_frame [0:TEST_FRAME_SIZE-1];
    integer i;
    
    // Initialize test frame
    initial begin
        // Frame header (little-endian bytes: 22 DD 11 EE 5A 5A 5A 5A)
        test_frame[0] = 8'h22;
        test_frame[1] = 8'hDD;
        test_frame[2] = 8'h11;
        test_frame[3] = 8'hEE;
        test_frame[4] = 8'h5A;
        test_frame[5] = 8'h5A;
        test_frame[6] = 8'h5A;
        test_frame[7] = 8'h5A;
        
        // Data pattern (0x00 to 0xFF repeating)
        for (i = 8; i < TEST_FRAME_SIZE - 8; i = i + 1) begin
            test_frame[i] = i[7:0];
        end
        
        // Frame trailer (little-endian bytes: 23 DD 11 EE 5A 5A 5A 5A)
        test_frame[TEST_FRAME_SIZE - 8] = 8'h23;
        test_frame[TEST_FRAME_SIZE - 7] = 8'hDD;
        test_frame[TEST_FRAME_SIZE - 6] = 8'h11;
        test_frame[TEST_FRAME_SIZE - 5] = 8'hEE;
        test_frame[TEST_FRAME_SIZE - 4] = 8'h5A;
        test_frame[TEST_FRAME_SIZE - 3] = 8'h5A;
        test_frame[TEST_FRAME_SIZE - 2] = 8'h5A;
        test_frame[TEST_FRAME_SIZE - 1] = 8'h5A;
        
        $display("Test frame initialized: %0d bytes", TEST_FRAME_SIZE);
        $display("Header: %02X %02X %02X %02X %02X %02X %02X %02X",
                 test_frame[0], test_frame[1], test_frame[2], test_frame[3],
                 test_frame[4], test_frame[5], test_frame[6], test_frame[7]);
        $display("Trailer: %02X %02X %02X %02X %02X %02X %02X %02X",
                 test_frame[TEST_FRAME_SIZE-8], test_frame[TEST_FRAME_SIZE-7],
                 test_frame[TEST_FRAME_SIZE-6], test_frame[TEST_FRAME_SIZE-5],
                 test_frame[TEST_FRAME_SIZE-4], test_frame[TEST_FRAME_SIZE-3],
                 test_frame[TEST_FRAME_SIZE-2], test_frame[TEST_FRAME_SIZE-1]);
    end
    
    // DUT signals
    wire        ddr_write_en;
    wire [ADDR_WIDTH-1:0] ddr_write_addr;
    wire [DATA_WIDTH-1:0] ddr_write_data;
    
    wire        frame_complete;
    wire [PAGE_ID_WIDTH-1:0] frame_page_id;
    wire [15:0] frame_id;
    
    // DDR memory model
    reg [7:0] ddr_memory [0:PAGE_SIZE*NUM_PAGES-1];
    reg [ADDR_WIDTH-1:0] last_write_addr;
    reg [DATA_WIDTH-1:0] last_write_data;
    
    // DDR write interface
    always @(posedge clk) begin
        if (ddr_write_en) begin
            ddr_memory[ddr_write_addr] <= ddr_write_data;
            last_write_addr <= ddr_write_addr;
            last_write_data <= ddr_write_data;
        end
    end
    
    // Frame writer instance
    wire        allocate_ok;
    wire [PAGE_ID_WIDTH-1:0] allocated_page;
    wire        allocate_req;
    wire        complete_write;
    wire [PAGE_ID_WIDTH-1:0] write_page_id;
    
    // Page manager signals
    reg [1:0] page_states [0:NUM_PAGES-1];
    reg [15:0] page_frame_ids [0:NUM_PAGES-1];
    reg [PAGE_ID_WIDTH-1:0] next_write_page;
    
    // Page manager logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            next_write_page <= 0;
            for (i = 0; i < NUM_PAGES; i = i + 1) begin
                page_states[i] <= 2'b00;  // FREE
                page_frame_ids[i] <= 16'hFFFF;
            end
        end else begin
            // Allocate page
            if (allocate_req) begin
                if (page_states[next_write_page] != 2'b11) begin  // Not READING
                    page_states[next_write_page] <= 2'b01;  // WRITING
                    page_frame_ids[next_write_page] <= frame_counter;
                    next_write_page <= (next_write_page + 1) % NUM_PAGES;
                end
            end
            
            // Complete write
            if (complete_write) begin
                page_states[write_page_id] <= 2'b10;  // READY
            end
        end
    end
    
    reg [15:0] frame_counter;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            frame_counter <= 0;
        end else if (allocate_req) begin
            frame_counter <= frame_counter + 1;
        end
    end
    
    assign allocate_ok = (page_states[next_write_page] != 2'b11);
    assign allocated_page = next_write_page;
    
    // Frame writer instance
    frame_writer #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH),
        .PAGE_ID_WIDTH(PAGE_ID_WIDTH)
    ) u_frame_writer (
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
    
    // Test stimulus
    reg data_valid;
    reg [DATA_WIDTH-1:0] data_in;
    reg frame_sent;
    reg [31:0] byte_count;
    
    initial begin
        // Wait for reset
        wait(rst_n);
        #(CLK_PERIOD * 5);
        
        // Send test frame byte by byte
        data_valid = 0;
        data_in = 0;
        frame_sent = 0;
        byte_count = 0;
        
        $display("\n=== Starting Frame Write Test ===");
        
        // Send frame data
        for (i = 0; i < TEST_FRAME_SIZE; i = i + 1) begin
            @(posedge clk);
            data_valid = 1;
            data_in = test_frame[i];
            byte_count = byte_count + 1;
        end
        
        // Deassert valid
        @(posedge clk);
        data_valid = 0;
        
        // Wait for frame complete
        frame_sent = 1;
        $display("Frame data sent: %0d bytes", byte_count);
    end
    
    // Monitor frame complete
    reg frame_done;
    initial begin
        frame_done = 0;
        wait(frame_complete && frame_sent);
        @(posedge clk);
        frame_done = 1;
        $display("\n=== Frame Complete ===");
        $display("Page ID: %0d", frame_page_id);
        $display("Frame ID: %0d", frame_id);
        $display("Page state: %0d", page_states[frame_page_id]);
        
        // Verify DDR data
        $display("\n=== Verifying DDR Data ===");
        begin
            integer j;
            integer errors;
            reg [ADDR_WIDTH-1:0] check_addr;
            errors = 0;
            check_addr = frame_page_id * PAGE_SIZE;
            
            for (j = 0; j < TEST_FRAME_SIZE; j = j + 1) begin
                if (ddr_memory[check_addr + j] != test_frame[j]) begin
                    $display("ERROR at byte %0d: expected %02X, got %02X", 
                             j, test_frame[j], ddr_memory[check_addr + j]);
                    errors = errors + 1;
                    if (errors >= 10) break;
                end
            end
            
            if (errors == 0) begin
                $display("✅ All %0d bytes match!", TEST_FRAME_SIZE);
            end else begin
                $display("❌ %0d errors found", errors);
            end
        end
        
        // Run read test
        $display("\n=== Starting Read Test ===");
        $finish;
    end
    
    // Simulation control
    initial begin
        $dumpfile("ddr_frame_buffer.vcd");
        $dumpvars(0, tb_ddr_frame_buffer);
    end
    
    initial begin
        $timeformat(-9, 0, " ns", 9);
        $display("DDR Frame Buffer Testbench");
        $display("CLK_PERIOD: %0d ns (%0d MHz)", CLK_PERIOD, 1000/CLK_PERIOD);
        $display("PAGE_SIZE: %0d bytes (%0d MB)", PAGE_SIZE, PAGE_SIZE/1024/1024);
        $display("NUM_PAGES: %0d", NUM_PAGES);
        $display("TEST_FRAME_SIZE: %0d bytes", TEST_FRAME_SIZE);
    end
    
    // Timeout
    initial begin
        #(CLK_PERIOD * 100000);
        $display("\n❌ Simulation timeout!");
        $finish;
    end

endmodule