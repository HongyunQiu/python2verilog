`timescale 1ns/1ps

module tb_uart;
    reg  clk, rst_n;
    reg  tx_start;
    reg  [7:0] tx_data_in;
    wire tx_busy, tx_done, tx_out;
    wire rx_done;
    wire [7:0] rx_data;
    wire rx_frame_err;
    wire [1:0] debug_tx_state, debug_rx_state;
    wire [3:0] debug_rx_bit;

    uart_transceiver #( .BAUD_DIVIDER(16) ) dut (
        .clk(clk), .rst_n(rst_n),
        .tx_start(tx_start), .tx_data_in(tx_data_in),
        .tx_busy(tx_busy), .tx_done(tx_done), .tx_out(tx_out),
        .rx_in(tx_out),  // 环回测试：TX 直接连 RX
        .rx_done(rx_done), .rx_data(rx_data), .rx_frame_err(rx_frame_err),
        .debug_tx_state(debug_tx_state),
        .debug_rx_state(debug_rx_state),
        .debug_rx_bit(debug_rx_bit)
    );

    // 系统时钟：50MHz，周期 20ns
    initial begin clk = 0; forever #10 clk = ~clk; end

    integer fout;
    integer errors;
    
    initial begin
        fout = $fopen("verilog_output.txt", "w");
        errors = 0;
        
        // 复位
        rst_n = 0;
        tx_start = 0;
        tx_data_in = 8'h00;
        #50;
        rst_n = 1;
        #20;
        
        // 测试向量
        test_byte(8'h55);
        test_byte(8'hAA);
        test_byte(8'h00);
        test_byte(8'hFF);
        test_byte(8'h12);
        test_byte(8'hAB);
        test_byte(8'h3C);
        test_byte(8'hE7);
        test_byte(8'h01);
        test_byte(8'hFE);
        test_byte(8'h80);
        test_byte(8'h7F);
        
        #100;
        
        if (errors == 0)
            $display("\n✅ 所有测试通过");
        else
            $display("\n❌ %d 个测试失败", errors);
        
        $fclose(fout);
        $finish;
    end
    
    task test_byte;
        input [7:0] data;
        begin
            // 等待空闲
            while (tx_busy || rx_done) #20;
            #20;
            
            // 启动发送
            tx_start = 1;
            tx_data_in = data;
            #20;
            tx_start = 0;
            
            // 等待接收完成
            while (!rx_done) #20;
            
            // 验证
            if (rx_data == data && !rx_frame_err) begin
                $display("PASS: TX=0x%02X → RX=0x%02X", data, rx_data);
            end else begin
                $display("FAIL: TX=0x%02X → RX=0x%02X err=%b", data, rx_data, rx_frame_err);
                errors = errors + 1;
            end
            
            $fwrite(fout, "TX=0x%02X RX=0x%02X err=%b\n", data, rx_data, rx_frame_err);
            
            // 等待 done 信号清除
            #20;
        end
    endtask

endmodule
