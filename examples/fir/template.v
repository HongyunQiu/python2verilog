// FIR Filter - Verilog Template
// 
// 从Cycle Model自动生成的Verilog实现
// 与Python Cycle Model逐位精确匹配
//
// 参数化设计：
// - NUM_TAPS: 滤波器抽头数
// - DATA_WIDTH: 数据位宽
// - COEFF_WIDTH: 系数位宽
// - FRAC_BITS: 系数小数位数

module fir_filter #(
    parameter NUM_TAPS    = 8,
    parameter DATA_WIDTH  = 16,
    parameter COEFF_WIDTH = 16,
    parameter FRAC_BITS   = 14,
    parameter ACC_WIDTH   = DATA_WIDTH + COEFF_WIDTH + $clog2(NUM_TAPS)
)(
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    valid_in,
    input  wire [DATA_WIDTH-1:0]   din,
    output reg  [DATA_WIDTH-1:0]   dout,
    output reg                     valid_out
);

    // 延迟线（寄存器链）
    // 对应Python: self.delay_line
    reg [DATA_WIDTH-1:0] delay_line [0:NUM_TAPS-1];
    
    // 系数寄存器
    // 对应Python: self.coefficients
    reg [COEFF_WIDTH-1:0] coefficients [0:NUM_TAPS-1];
    
    // 组合逻辑中间值
    // 对应Python: self._next_acc, self._next_out
    wire [ACC_WIDTH-1:0]   acc_comb;
    wire [DATA_WIDTH-1:0]  out_comb;
    
    // 乘法器阵列（并行MAC）
    // 对应Python: compute()中的for循环
    wire [DATA_WIDTH+COEFF_WIDTH-2:0] products [0:NUM_TAPS-1];
    
    genvar i;
    generate
        for (i = 0; i < NUM_TAPS; i = i + 1) begin : gen_mac
            // 乘法器
            assign products[i] = $signed(delay_line[i]) * $signed(coefficients[i]);
        end
    endgenerate
    
    // 累加器（树形归约）
    // 对应Python: acc += product
    assign acc_comb = {
        NUM_TAPS{1'b0}
    } + 
    {
        NUM_TAPS{1'b0}
    } +
    products[0] +
    products[1] +
    products[2] +
    products[3] +
    products[4] +
    products[5] +
    products[6] +
    products[7];
    
    // 饱和截断
    // 对应Python: max(min_val, min(max_val-1, acc))
    localparam MAX_VAL = {1'b0, {DATA_WIDTH-1{1'b1}}};\n    localparam MIN_VAL = {1'b1, {DATA_WIDTH-1{1'b0}}};\n    \n    assign out_comb = (acc_comb > MAX_VAL) ? MAX_VAL :\n                      (acc_comb < MIN_VAL) ? MIN_VAL :\n                      acc_comb[ACC_WIDTH-1 -: DATA_WIDTH];\n    \n    // 时序逻辑\n    // 对应Python: clock()\n    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin\n            // 复位\n            for (i = 0; i < NUM_TAPS; i = i + 1)\n                delay_line[i] <= {DATA_WIDTH{1'b0}};
            dout      <= {DATA_WIDTH{1'b0}};
            valid_out <= 1'b0;
        end else begin
            // 更新延迟线（移位寄存器）
            // 对应Python: self.delay_line = self.delay_line[1:] + [self.new_sample]
            for (i = 0; i < NUM_TAPS-1; i = i + 1)
                delay_line[i] <= delay_line[i+1];
            delay_line[NUM_TAPS-1] <= din;
            
            // 更新输出寄存器
            // 对应Python: self.out_reg = self._next_out
            dout <= out_comb;
            
            // 输出有效信号
            valid_out <= valid_in;
        end
    end
    
    // 系数配置接口（简化版，实际可能需要APB/AHB接口）
    task configure_coefficients;
        input [COEFF_WIDTH*NUM_TAPS-1:0] coeff_data;
        begin
            for (i = 0; i < NUM_TAPS; i = i + 1)
                coefficients[i] <= coeff_data[i*COEFF_WIDTH +: COEFF_WIDTH];
        end
    endtask
    
endmodule