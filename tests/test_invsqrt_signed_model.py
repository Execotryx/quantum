import numpy as np

from qcompile.invsqrt.direct import DirectFormat, coefficient_table
from qcompile.invsqrt.signed_model import booth_digits, signed_phase64


def test_radix_four_digits_reconstruct_every_13_bit_word():
    for width in range(1, 14):
        values = np.arange(1 << width, dtype=np.int64)
        digits = booth_digits(values, width)
        assert len(digits) == (width + 2) // 2
        assert all(np.all((digit >= -2) & (digit <= 2)) for digit in digits)
        assert np.array_equal(sum(digit << (2 * i) for i, digit in enumerate(digits)), values)


def test_signed_model_small_input_shape():
    fmt = DirectFormat(3, 2, (13, 9, 5))
    xs = np.arange(1, 148, dtype=np.int64)
    table = coefficient_table(fmt)
    expected = []
    for x in xs.tolist():
        exponent = max(i for i in range(fmt.n_p + 1) if 4**i <= x)
        left = fmt.n_p - exponent
        normalized = x << (2 * left)
        low_width = 2 * fmt.n_p - fmt.segment_bits
        row = table[(normalized >> low_width) - (1 << fmt.segment_bits)]
        t = normalized & ((1 << low_width) - 1)
        value = row[-1]
        for j in (1, 0):
            mask = (1 << fmt.widths[j]) - 1
            product = 0
            for i in range((low_width + 2) // 2):
                digit = ((t >> (2 * i - 1)) & 1 if i else 0) + ((t >> (2 * i)) & 1)
                digit -= 2 * ((t >> (2 * i + 1)) & 1)
                shift = fmt.fractional[j] - fmt.fractional[j + 1] + 2 * i - 2 * fmt.n_p
                term = digit * value
                term = term << shift if shift >= 0 else term >> -shift
                product = (product + term) & mask
            value = (row[j] - product) & mask
        expected.append(((value << left) << (64 - fmt.output_fractional)) % (1 << 64))
    assert np.array_equal(signed_phase64(fmt, table, xs), np.array(expected, dtype=np.uint64))
