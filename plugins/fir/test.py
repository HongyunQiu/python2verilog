#!/usr/bin/env python3
"""FIR Filter - Verification Script"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden import generate_test_vectors
from cycle import FIRCycleModel, convert_coefficients_to_fixed_point


def test_golden_vs_cycle(num_samples=20, num_taps=4, seed=42):
    print("=" * 60)
    print("测试1: Golden Model vs Cycle Model")
    print("=" * 60)
    
    input_samples, float_coeffs, golden_output = generate_test_vectors(
        num_samples=num_samples, num_taps=num_taps, seed=seed)
    
    fixed_coeffs = convert_coefficients_to_fixed_point(float_coeffs, frac_bits=14)
    
    cycle_model = FIRCycleModel(num_taps=num_taps, data_width=16)
    cycle_model.configure(fixed_coeffs)
    cycle_output = cycle_model.run(input_samples)
    
    print(f"输入样本数: {num_samples}")
    print(f"滤波器抽头: {num_taps}")
    print(f"Golden输出前5个: {golden_output[:5]}")
    print(f"Cycle输出前5个:  {cycle_output[:5]}")
    
    if len(golden_output) != len(cycle_output):
        print(f"FAIL: 长度不匹配 {len(golden_output)} vs {len(cycle_output)}")
        return False
        
    max_error = max(abs(g - c) for g, c in zip(golden_output, cycle_output))
    print(f"最大误差: {max_error}")
    
    if max_error <= 2:
        print("PASS")
        return True
    else:
        print("FAIL: 误差过大")
        return False


def gen_tb(input_samples, coefficients, num_taps):
    lines = []
    lines.append("`timescale 1ns/1ps")
    lines.append("")
    lines.append("module tb_fir_filter;")
    lines.append("    reg  clk, rst_n, valid_in;")
    lines.append("    reg  [15:0] din;")
    lines.append("    wire [15:0] dout;")
    lines.append("    wire        valid_out;")
    lines.append("")
    lines.append(f"    fir_filter #( .NUM_TAPS({num_taps}) ) dut (")
    lines.append("        .clk(clk), .rst_n(rst_n), .valid_in(valid_in),")
    lines.append("        .din(din), .dout(dout), .valid_out(valid_out)")
    lines.append("    );")
    lines.append("")
    lines.append("    initial begin clk=0; forever #5 clk=~clk; end")
    lines.append("")
    lines.append("    initial begin")
    lines.append("        rst_n=0; valid_in=0; din=16'd0;")
    lines.append("        #20 rst_n=1;")
    for i, c in enumerate(coefficients):
        lines.append(f"        coefficients[{i}] = 16'{c};")
    for s in input_samples:
        lines.append(f"        #10 din = 16'{s}; valid_in = 1'b1;")
    lines.append("        #20 $finish;")
    lines.append("    end")
    lines.append("")
    lines.append("    integer fout;")
    # 使用单引号避免冲突
    lines.append("    initial fout = $fopen('verilog_output.txt', 'w');")
    lines.append("")
    lines.append("    always @(posedge clk)")
    lines.append("        if (valid_out) $fwrite(fout, '%d\n', dout);")
    lines.append("")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def test_verilog_simulation(num_samples=20, num_taps=4, seed=42):
    print()
    print("=" * 60)
    print("测试2: Cycle Model vs Verilog")
    print("=" * 60)
    
    work_dir = os.path.dirname(os.path.abspath(__file__))
    artifacts_dir = os.path.join(work_dir, "..", "..", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    input_samples, float_coeffs, _ = generate_test_vectors(
        num_samples=num_samples, num_taps=num_taps, seed=seed)
    fixed_coeffs = convert_coefficients_to_fixed_point(float_coeffs, frac_bits=14)
    
    cycle_model = FIRCycleModel(num_taps=num_taps, data_width=16)
    cycle_model.configure(fixed_coeffs)
    cycle_output = cycle_model.run(input_samples)
    
    tb_content = gen_tb(input_samples, fixed_coeffs, num_taps)
    tb_file = os.path.join(artifacts_dir, "tb_fir.v")
    with open(tb_file, "w") as f:
        f.write(tb_content)
    
    print(f"测试平台: {tb_file}")
    
    result = subprocess.run(
        ["iverilog", "-o", os.path.join(artifacts_dir, "firmware"),
         tb_file, os.path.join(work_dir, "template.v")],
        capture_output=True, text=True, timeout=30)
    
    if result.returncode != 0:
        print(f"编译失败:")
        print(result.stderr[:500])
        return False
    
    print("编译成功")
    
    result = subprocess.run(
        ["vvp", os.path.join(artifacts_dir, "firmware")],
        capture_output=True, text=True, timeout=30,
        cwd=artifacts_dir)
    
    if result.returncode != 0:
        print(f"仿真失败:")
        print(result.stderr[:500])
        return False
    
    output_file = os.path.join(artifacts_dir, "verilog_output.txt")
    if not os.path.exists(output_file):
        print("输出文件未生成")
        return False
    
    with open(output_file, "r") as f:
        verilog_output = [int(line.strip()) for line in f if line.strip()]
    
    print(f"Cycle输出前5个:  {cycle_output[:5]}")
    print(f"Verilog输出前5个: {verilog_output[:5]}")
    
    if len(cycle_output) != len(verilog_output):
        print(f"长度不匹配: {len(cycle_output)} vs {len(verilog_output)}")
        return False
    
    mismatches = sum(1 for c, v in zip(cycle_output, verilog_output) if c != v)
    print(f"不匹配数: {mismatches}/{len(cycle_output)}")
    
    if mismatches == 0:
        print("完全匹配！")
        return True
    elif mismatches <= 2:
        print("基本通过（少量不匹配）")
        return True
    else:
        print("失败（不匹配过多）")
        return False


if __name__ == "__main__":
    pass1 = test_golden_vs_cycle()
    pass2 = test_verilog_simulation()
    
    print()
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    status1 = "PASS" if pass1 else "FAIL"
    status2 = "PASS" if pass2 else "FAIL"
    print(f"Golden vs Cycle: {status1}")
    print(f"Cycle vs Verilog: {status2}")
    
    if pass1 and pass2:
        print()
        print("所有测试通过！FIR插件验证成功。")
    else:
        print()
        print("部分测试失败，需要调试。")
