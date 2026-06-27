#!/usr/bin/env python3
"""FIR Filter - Golden Model"""

import numpy as np
from typing import List, Tuple


def fir_filter_golden(input_samples, coefficients, data_width=16):
    num_taps = len(coefficients)
    max_val = 2**(data_width-1)
    min_val = -max_val
    output = []
    extended_input = [0] * (num_taps - 1) + input_samples
    for i in range(len(input_samples)):
        acc = 0.0
        for j in range(num_taps):
            acc += extended_input[i + j] * coefficients[j]
        acc = max(min_val, min(max_val - 1, int(round(acc))))
        output.append(acc)
    return output


def generate_test_vectors(num_samples=100, num_taps=8, data_width=16, seed=42):
    np.random.seed(seed)
    max_val = 2**(data_width-1)
    input_samples = np.random.randint(-max_val//2, max_val//2,
                                       size=num_samples, dtype=np.int32)
    input_samples = input_samples.tolist()
    
    cutoff = 0.2
    coefficients = []
    for n in range(num_taps):
        if n == (num_taps - 1) // 2:
            coeff = 2 * np.pi * cutoff
        else:
            numerator = np.sin(2 * np.pi * cutoff * (n - (num_taps - 1) // 2))
            denominator = np.pi * (n - (num_taps - 1) // 2)
            coeff = numerator / denominator
        window = 0.5 * (1 - np.cos(2 * np.pi * n / (num_taps - 1)))
        coeff *= window
        coefficients.append(coeff)
    
    coeff_sum = sum(coefficients)
    coefficients = [c / coeff_sum for c in coefficients]
    
    expected_output = fir_filter_golden(input_samples, coefficients, data_width)
    return input_samples, coefficients, expected_output


if __name__ == "__main__":
    input_samples, coefficients, expected_output = generate_test_vectors(
        num_samples=10, num_taps=4, data_width=16)
    print("输入样本:", input_samples)
    print("滤波器系数:", [f"{c:.6f}" for c in coefficients])
    print("期望输出:", expected_output)
    actual_output = fir_filter_golden(input_samples, coefficients, 16)
    assert actual_output == expected_output, "Golden Model自验证失败！"
    print("Golden Model自验证通过")
