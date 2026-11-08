"""Separate shift/reduce table backend, with primitive-generator validation."""

from qcompile.errors import ValidationError


class GF4096:
    modulus = 0x1053
    order = 4095

    def __init__(self):
        self.exp = []
        self.log = [-1] * 4096
        x = 1
        for exponent in range(self.order):
            if self.log[x] != -1:
                raise ValidationError("alpha is not primitive for this modulus")
            self.exp.append(x)
            self.log[x] = exponent
            x <<= 1
            if x & 4096:
                x ^= self.modulus
        if x != 1 or any(v == -1 for v in self.log[1:]):
            raise ValidationError("field table is incomplete")

    @staticmethod
    def symbol(value):
        if type(value) is not int or not 0 <= value < 4096:
            raise ValidationError("field symbol out of range")
        return value

    def mul(self, a, b):
        self.symbol(a)
        self.symbol(b)
        return 0 if a == 0 or b == 0 else self.exp[(self.log[a] + self.log[b]) % self.order]

    def inv(self, a):
        self.symbol(a)
        if a == 0:
            raise ZeroDivisionError("zero has no field inverse")
        return self.exp[-self.log[a] % self.order]

    def div(self, a, b):
        return self.mul(a, self.inv(b))

    def evaluate(self, coefficients, x):
        value = 0
        for coefficient in reversed(coefficients):
            value = self.mul(value, x) ^ coefficient
        return value

    def fixed_map(self, multiplier):
        self.symbol(multiplier)
        return [self.mul(1 << i, multiplier) for i in range(12)]

    def square_map(self):
        return [self.mul(1 << i, 1 << i) for i in range(12)]

    @staticmethod
    def apply_map(columns, value):
        GF4096.symbol(value)
        if len(columns) != 12:
            raise ValidationError("a field linear map needs 12 columns")
        result = 0
        for i in range(12):
            if value >> i & 1:
                result ^= columns[i]
        return result
