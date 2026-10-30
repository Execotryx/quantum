"""Transparent carryless polynomial reference. No log tables or generator code."""

from qcompile.errors import ValidationError

MODULUS = (1 << 12) | (1 << 6) | (1 << 4) | (1 << 1) | 1


def multiply(a: int, b: int, modulus=MODULUS) -> int:
    degree = modulus.bit_length() - 1
    if type(a) is not int or type(b) is not int or not 0 <= a < 1 << degree or not 0 <= b < 1 << degree:
        raise ValidationError("field symbol out of range")
    product = 0
    for bit in range(degree):
        if b >> bit & 1:
            product ^= a << bit
    for bit in range(product.bit_length() - 1, degree - 1, -1):
        if product >> bit & 1:
            product ^= modulus << (bit - degree)
    return product


def power(a, exponent):
    if type(exponent) is not int or exponent < 0:
        raise ValidationError("negative/noninteger field exponent")
    result = 1
    while exponent:
        if exponent & 1:
            result = multiply(result, a)
        a = multiply(a, a)
        exponent >>= 1
    return result


def inverse(a):
    if a == 0:
        raise ZeroDivisionError("zero has no field inverse")
    return power(a, 4094)
