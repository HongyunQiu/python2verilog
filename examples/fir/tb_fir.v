`timescale 1ns/1ps

module tb_fir_filter;
    reg  clk, rst_n, valid_in;
    reg  [15:0] din;
    wire [15:0] dout;
    wire        valid_out;

    fir_filter #( .NUM_TAPS(4) ) dut (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .din(din), .dout(dout), .valid_out(valid_out)
    );

    initial begin clk=0; forever #5 clk=~clk; end

    initial begin
        rst_n=0; valid_in=0; din=16'd0;
        #20 rst_n=1;
        coefficients[0] = 16'0;
        coefficients[1] = 16'13203;
        coefficients[2] = 16'3181;
        coefficients[3] = 16'0;
        #10 din = 16'7270; valid_in = 1'b1;
        #10 din = 16'-589; valid_in = 1'b1;
        #10 din = 16'-15524; valid_in = 1'b1;
        #10 din = 16'-10994; valid_in = 1'b1;
        #10 din = 16'13418; valid_in = 1'b1;
        #10 din = 16'5191; valid_in = 1'b1;
        #10 din = 16'-4420; valid_in = 1'b1;
        #10 din = 16'-5100; valid_in = 1'b1;
        #10 din = 16'5734; valid_in = 1'b1;
        #10 din = 16'-10119; valid_in = 1'b1;
        #10 din = 16'466; valid_in = 1'b1;
        #10 din = 16'13526; valid_in = 1'b1;
        #10 din = 16'-11958; valid_in = 1'b1;
        #10 din = 16'5578; valid_in = 1'b1;
        #10 din = 16'-1961; valid_in = 1'b1;
        #10 din = 16'11636; valid_in = 1'b1;
        #10 din = 16'-5021; valid_in = 1'b1;
        #10 din = 16'11111; valid_in = 1'b1;
        #10 din = 16'-361; valid_in = 1'b1;
        #10 din = 16'-8062; valid_in = 1'b1;
        #20 $finish;
    end

    integer fout;
    initial fout = $fopen('verilog_output.txt', 'w');

    always @(posedge clk)
        if (valid_out) $fwrite(fout, '%d
', dout);

endmodule
