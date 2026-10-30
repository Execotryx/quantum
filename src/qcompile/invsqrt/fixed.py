from dataclasses import dataclass
from fractions import Fraction

from qcompile.errors import ValidationError
from qcompile.io import nonnegative_int, positive_int


@dataclass(frozen=True)
class Format:
    width: int
    fractional: int
    signed: bool = False
    rounding: str = "nearest_even"
    overflow: str = "reject"

    def __post_init__(self):
        positive_int(self.width, "width")
        nonnegative_int(self.fractional, "fractional")
        if self.rounding not in ("floor", "toward_zero", "nearest_even") or self.overflow not in (
            "reject",
            "wrap",
        ):
            raise ValidationError("unsupported finite-width policy")

    def encode(self, value) -> int:
        scaled = Fraction(value) * (1 << self.fractional)
        if self.rounding == "floor":
            word = scaled.numerator // scaled.denominator
        elif self.rounding == "toward_zero":
            word = int(scaled)
        else:
            word = round(scaled)
        minimum = -(1 << (self.width - 1)) if self.signed else 0
        maximum = (1 << (self.width - int(self.signed))) - 1
        if not minimum <= word <= maximum:
            if self.overflow == "reject":
                raise ValidationError("fixed-point overflow")
            word = (word - minimum) % (1 << self.width) + minimum
        return word

    def decode(self, word: int) -> Fraction:
        return Fraction(word, 1 << self.fractional)

    def quantize(self, value) -> Fraction:
        return self.decode(self.encode(value))


def polynomial_model(config):
    """Horner + optional Newton step on x/4^e in [1,4), with explicit quantization.

    Coefficients are supplied frozen rational strings, not fitted silently.
    Each multiply/add/Newton expression is rounded separately. Scaling uses
    arithmetic shifts through the same declared format.
    """
    fmt = Format(**config["format"])
    tables = [[fmt.quantize(Fraction(c)) for c in row] for row in config["coefficients"]]
    if not tables or any(not row for row in tables):
        raise ValidationError("empty coefficient table")
    steps = config.get("newton_steps", 0)
    if type(steps) is not int or steps not in (0, 1):
        raise ValidationError("newton_steps must be 0 or 1")

    def evaluate(x):
        positive_int(x, "x")
        exponent = (x.bit_length() - 1) // 2
        z = fmt.quantize(Fraction(x, 1 << (2 * exponent)))
        index = min(len(tables) - 1, int((z - 1) * len(tables) / 3))
        y = tables[index][-1]
        for coefficient in reversed(tables[index][:-1]):
            y = fmt.quantize(fmt.quantize(y * z) + coefficient)
        for _ in range(steps):
            square = fmt.quantize(y * y)
            product = fmt.quantize(z * square)
            correction = fmt.quantize(3 - product)
            y = fmt.quantize(fmt.quantize(y * correction) / 2)
        phase = fmt.quantize(y / (1 << exponent))
        return round(phase * (1 << 64)) % (1 << 64)

    return evaluate
