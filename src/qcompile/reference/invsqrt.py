"""Integer brackets independent of the finite-width approximation implementation.

The exact official 64-bit rounding convention remains a G0 reconciliation item.
The bracket is mathematically rigorous and deliberately does not claim parity
with an unavailable official phase accumulator.
"""

import math
import time
from decimal import Decimal, localcontext

from qcompile.errors import ValidationError
from qcompile.io import positive_int

MAX_INPUT = 3_133_452
PHASE_BITS = 64


def phase_floor(x: int, bits: int = PHASE_BITS) -> int:
    positive_int(x, "x")
    positive_int(bits, "bits")
    return math.isqrt((1 << (2 * bits)) // x)


def phase_nearest_even(x: int, bits: int = PHASE_BITS) -> int:
    q = phase_floor(x, bits)
    comparison = (1 << (2 * bits + 2)) - x * (2 * q + 1) ** 2
    return q + int(comparison > 0 or (comparison == 0 and q % 2 == 1))


def circular_units(a: int, b: int, bits=PHASE_BITS) -> int:
    modulus = 1 << bits
    return (a - b + modulus // 2) % modulus - modulus // 2


def decimal_margin(x: int, phase_word: int, bits=PHASE_BITS) -> Decimal:
    positive_int(x, "x")
    with localcontext() as ctx:
        ctx.prec = 90
        target = 1 / Decimal(x).sqrt()
        delta = Decimal(phase_word) / (1 << bits) - target
        delta -= (delta + Decimal("0.5")).to_integral_value(rounding="ROUND_FLOOR")
        return +(target / (1 << 24) - abs(delta))


def scan(evaluate, *, first=1, last=MAX_INPUT, chunk_size=8192, progress=None) -> dict:
    """Exhaustive conservative scan of integer phase words, memory O(chunk_size).

    Uses an interval for the irrational target. Nonpositive lower bounds are
    inconclusive/failing engineering margins, never certified official failures.
    No float subtraction is used; margin units are 2^-88 turns.
    """
    positive_int(first, "first")
    positive_int(last, "last")
    positive_int(chunk_size, "chunk_size")
    if last < first or last > MAX_INPUT:
        raise ValidationError("invalid scan domain")
    minimum = None
    worst = None
    failed = 0
    histogram = [0] * 8
    started = time.monotonic()
    scale = 1 << PHASE_BITS
    for start in range(first, last + 1, chunk_size):
        stop = min(last + 1, start + chunk_size)
        for x in range(start, stop):
            word = evaluate(x)
            if type(word) is not int or not 0 <= word < scale:
                raise ValidationError(f"invalid unsigned 64-bit phase word at x={x}")
            low = phase_floor(x)
            exact = low * low * x == scale * scale
            high = low if exact else low + 1
            error = max(abs(circular_units(word, low)), abs(circular_units(word, high)))
            margin = low - (error << 24)
            failed += margin <= 0
            if minimum is None or margin < minimum:
                minimum, worst = margin, x
            fraction = max(0, min(7, margin * 8 // max(1, low)))
            histogram[fraction] += 1
        if progress:
            progress(stop - first, last - first + 1)
    return {
        "kind": "independent_numerical_bound",
        "official_compatible": False,
        "first": first,
        "last": last,
        "completed": last - first + 1,
        "expected": last - first + 1,
        "full_domain": first == 1 and last == MAX_INPUT,
        "nonpositive_margin_count": failed,
        "worst_input": worst,
        "minimum_margin_units_2_pow_minus_88": minimum,
        "minimum_margin_turns": minimum / (1 << 88),
        "minimum_margin_phase64_units": minimum / (1 << 24),
        "margin_histogram_eighths_of_tolerance": histogram,
        "elapsed_seconds": time.monotonic() - started,
    }
