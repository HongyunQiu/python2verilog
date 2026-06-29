// tb_simple.v - Simplified DDR Frame Buffer Testbench
// Pure Verilog-2001 syntax for Icarus Verilog compatibility

`timescale 1ns/1ps

module tb_simple;

    // Parameters
    parameter CLK_PERIOD = 10;  // 100 MHz
    parameter DATA_WIDTH = 8;
    parameter ADDR_WIDTH = 32;
    parameter PAGE_ID_WIDTH = 7;
    parameter NUM_PAGES = 51;
    parameter PAGE_SIZE = 20971520;  // 20MB
    
    // Simplified frame size for testing (header + 200 bytes + trailer)
    parameter TEST_FRAME_SIZE = 216;
    
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
    
    // Test signals
    reg data_valid;
    reg [DATA_WIDTH-1:0] data_in;
    reg [TEST_FRAME_SIZE-1:0] test_byte_idx;
    reg frame_sent;
    reg frame_done;
    reg [31:0] errors;
    
    // DUT signals
    wire        ddr_write_en;
    wire [ADDR_WIDTH-1:0] ddr_write_addr;
    wire [DATA_WIDTH-1:0] ddr_write_data;
    
    wire        allocate_req;
    wire        allocate_ok;
    wire [PAGE_ID_WIDTH-1:0] allocated_page;
    wire        complete_write;
    wire [PAGE_ID_WIDTH-1:0] write_page_id;
    
    wire        frame_complete;
    wire [PAGE_ID_WIDTH-1:0] frame_page_id;
    wire [15:0] frame_id;
    
    // DDR memory model (simplified - only track written bytes)
    reg [7:0] ddr_memory [0:4095];  // Track first 4KB for verification
    reg [31:0] write_count;
    
    // DDR write interface
    always @(posedge clk) begin
        if (ddr_write_en) begin
            if (ddr_write_addr < 4096) begin
                ddr_memory[ddr_write_addr] <= ddr_write_data;
            end
            write_count <= write_count + 1;
        end
    end
    
    // Page manager (simplified)
    reg [1:0] page_states [0:NUM_PAGES-1];
    reg [15:0] page_frame_ids [0:NUM_PAGES-1];
    reg [PAGE_ID_WIDTH-1:0] next_write_page;
    reg [15:0] frame_counter;
    integer i_pm;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            next_write_page <= 0;
            frame_counter <= 0;
            for (i_pm = 0; i_pm < NUM_PAGES; i_pm = i_pm + 1) begin
                page_states[i_pm] <= 2'b00;  // FREE
                page_frame_ids[i_pm] <= 16'hFFFF;
            end
        end else begin
            // Allocate page
            if (allocate_req) begin
                if (page_states[next_write_page] != 2'b11) begin  // Not READING
                    page_states[next_write_page] <= 2'b01;  // WRITING
                    page_frame_ids[next_write_page] <= frame_counter;
                    frame_counter <= frame_counter + 1;
                    next_write_page <= (next_write_page + 1) % NUM_PAGES;
                end
            end
            
            // Complete write
            if (complete_write) begin
                page_states[write_page_id] <= 2'b10;  // READY
            end
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
    
    // Test stimulus - send simplified frame
    initial begin
        // Wait for reset
        wait(rst_n);
        #(CLK_PERIOD * 5);
        
        $display("\n=== Starting Frame Write Test ===");
        $display("TEST_FRAME_SIZE: %0d bytes", TEST_FRAME_SIZE);
        
        data_valid = 0;
        data_in = 0;
        frame_sent = 0;
        test_byte_idx = 0;
        write_count = 0;
        
        // Send frame header (little-endian: 22 DD 11 EE 5A 5A 5A 5A)
        @(posedge clk); data_valid = 1; data_in = 8'h22;
        @(posedge clk); data_valid = 1; data_in = 8'hDD;
        @(posedge clk); data_valid = 1; data_in = 8'h11;
        @(posedge clk); data_valid = 1; data_in = 8'hEE;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        
        // Send data pattern (0x00 to 0xC8)
        for (test_byte_idx = 8; test_byte_idx < TEST_FRAME_SIZE - 8; test_byte_idx = test_byte_idx + 1) begin
            @(posedge clk);
            data_valid = 1;
            data_in = test_byte_idx[7:0];
        end
        
        // Send frame trailer (little-endian: 23 DD 11 EE 5A 5A 5A 5A)
        @(posedge clk); data_valid = 1; data_in = 8'h23;
        @(posedge clk); data_valid = 1; data_in = 8'hDD;
        @(posedge clk); data_valid = 1; data_in = 8'h11;
        @(posedge clk); data_valid = 1; data_in = 8'hEE;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        @(posedge clk); data_valid = 1; data_in = 8'h5A;
        
        // Deassert valid
        @(posedge clk);
        data_valid = 0;
        frame_sent = 1;
        
        $display("Frame data sent: %0d bytes", TEST_FRAME_SIZE);
    end
    
    // Monitor frame complete and verify
    initial begin
        frame_done = 0;
        errors = 0;
        
        wait(frame_complete && frame_sent);
        @(posedge clk);
        frame_done = 1;
        
        $display("\n=== Frame Complete ===");
        $display("Page ID: %0d", frame_page_id);
        $display("Frame ID: %0d", frame_id);
        $display("Page state: %0d (expected 2=READY)", page_states[frame_page_id]);
        $display("Write count: %0d (expected %0d)", write_count, TEST_FRAME_SIZE);
        
        // Verify DDR data
        $display("\n=== Verifying DDR Data ===");
        begin
            integer j;
            integer err_count;
            err_count = 0;
            
            // Check header
            if (ddr_memory[0] != 8'h22) begin $display(\"ERROR byte 0: expected 22, got %h\", ddr_memory[0]); err_count = err_count + 1; end\n            if (ddr_memory[1] != 8'hDD) begin $display("ERROR byte 1: expected DD, got %h", ddr_memory[1]); err_count = err_count + 1; end
            if (ddr_memory[2] != 8'h11) begin $display("ERROR byte 2: expected 11, got %h", ddr_memory[2]); err_count = err_count + 1; end
            if (ddr_memory[3] != 8'hEE) begin $display("ERROR byte 3: expected EE, got %h", ddr_memory[3]); err_count = err_count + 1; end
            if (ddr_memory[4] != 8'h5A) begin $display("ERROR byte 4: expected 5A, got %h", ddr_memory[4]); err_count = err_count + 1; end
            if (ddr_memory[5] != 8'h5A) begin $display("ERROR byte 5: expected 5A, got %h", ddr_memory[5]); err_count = err_count + 1; end
            if (ddr_memory[6] != 8'h5A) begin $display("ERROR byte 6: expected 5A, got %h", ddr_memory[6]); err_count = err_count + 1; end
            if (ddr_memory[7] != 8'h5A) begin $display("ERROR byte 7: expected 5A, got %h", ddr_memory[7]); err_count = err_count + 1; end
            
            // Check data pattern
            for (j = 8; j < TEST_FRAME_SIZE - 8; j = j + 1) begin
                if (ddr_memory[j] != j[7:0]) begin
                    $display("ERROR byte %0d: expected %02X, got %02X", j, j[7:0], ddr_memory[j]);
                    err_count = err_count + 1;
                    if (err_count >= 10) break;
                end
            end
            
            // Check trailer
            if (ddr_memory[TEST_FRAME_SIZE-8] != 8'h23) begin $display("ERROR trailer byte 0: expected 23, got %h", ddr_memory[TEST_FRAME_SIZE-8]); err_count = err_count + 1; end
            if (ddr_memory[TEST_FRAME_SIZE-7] != 8'hDD) begin $display("ERROR trailer byte 1: expected DD, got %h", ddr_memory[TEST_FRAME_SIZE-7]); err_count = err_count + 1; end
            if (ddr_memory[TEST_FRAME_SIZE-6] != 8'h11) begin $display("ERROR trailer byte 2: expected 11, got %h", ddr_memory[TEST_FRAME_SIZE-6]); err_count = err_count + 1; end
            if (ddr_memory[TEST_FRAME_SIZE-5] != 8'hEE) begin $display("ERROR trailer byte 3: expected EE, got %h", ddr_memory[TEST_FRAME_SIZE-5]); err_count = err_count + 1; end
            if (ddr_memory[TEST_FRAME_SIZE-4] != 8'h5A) begin $display("ERROR trailer byte 4: expected 5A, got %h", ddr_memory[TEST_FRAME_SIZE-4]); err_count = err_count + 1; end
            if (ddr_memory[TEST_FRAME_SIZE-3] != 8'h5A) begin $display("ERROR trailer byte 5: expected 5A, got %h", ddr_memory[TEST_FRAME_SIZE-3]); err_count = err_count + 1; end
            if (ddr_memory[TEST_FRAME_SIZE-2] != 8'h5A) begin $display("ERROR trailer byte 6: expected 5A, got %h", ddr_memory[TEST_FRAME_SIZE-2]); err_count = err_count + 1; end
            if (ddr_memory[TEST_FRAME_SIZE-1] != 8'h5A) begin $display("ERROR trailer byte 7: expected 5A, got %h", ddr_memory[TEST_FRAME_SIZE-1]); err_count = err_count + 1; end
            
            errors = err_count;
            
            if (err_count == 0) begin
                $display("✅ All %0d bytes match!", TEST_FRAME_SIZE);
            end else begin
                $display("❌ %0d errors found", err_count);
            end
        end
        
        // Summary
        $display("\n=== Test Summary ===");
        if (errors == 0 && page_states[frame_page_id] == 2'b10) begin
            $display("✅ ALL TESTS PASSED!");
        end else begin
            $display("❌ TESTS FAILED");
        end
        
        $finish;
    end
    
    // Simulation control
    initial begin
        $dumpfile("ddr_frame_buffer.vcd");
        $dumpvars(0, tb_simple);
    end
    
    initial begin
        $timeformat(-9, 0, " ns", 9);
        $display("DDR Frame Buffer Simple Testbench");
        $display("CLK_PERIOD: %0d ns (%0d MHz)", CLK_PERIOD, 1000/CLK_PERIOD);
        $display("TEST_FRAME_SIZE: %0d bytes", TEST_FRAME_SIZE);
    end
    
    // Timeout
    initial begin
        #(CLK_PERIOD * 100000);
        $display("\n❌ Simulation timeout!");
        $finish;
    end

endmodule