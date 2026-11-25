"""Exact top-first interpolation for the incumbent linear-quotient division.

The high interpolation coordinate is applied before the quotient constant
is divided.  Finite interpolation columns have zero high coordinate, so
that quotient word can then be used as a read-only operand.  All operand
linear forms borrow existing words and are restored.  The zero-safe scalar
extension and the central first-gap schedule are unchanged.
"""
from contextlib import contextmanager
from functools import cache


@cache
def columns(m):
    from inplace_poly import GF, interpolation_columns
    finite = tuple(tuple(col) + (0,) for col in interpolation_columns(m))
    high = [1]
    for point in range(m):
        new = [0] * (len(high) + 1)
        for i, value in enumerate(high):
            new[i] ^= GF.mul(point, value)
            new[i+1] ^= value
        high = new
    assert high[-1] == 1
    return finite, tuple(high)


def divide_locator(b, p, d, scale, counts, *, reverse=False, monic=False):
    from inplace_poly import GF, linear_form, vector_product
    n = len(d)
    assert len(p) == n + (0 if monic else 1)
    qh = scale.inverse if monic else p[n]
    ql = p[n-1]
    poly = d[:-1]
    m = len(poly)
    targets = p[:n]

    def high_scale():
        if not monic:
            scale.apply(p[n], divide=not reverse)

    def high_update():
        if not m:
            return
        _, high = columns(m)
        counts['products'] += vector_product(b, qh, poly[-1], targets, high)

    def constant_scale():
        scale.apply(ql, divide=not reverse)

    def finite_update():
        if not m:
            return
        finite, _ = columns(m)
        points = reversed(range(m)) if reverse else range(m)
        for point in points:
            with linear_form(b, [ql, qh], [1, point]) as lhs:
                with linear_form(b, poly, [GF.pow(point, i) for i in range(m)]) as rhs:
                    counts['products'] += vector_product(b, lhs, rhs, targets, finite[point])

    actions = [high_scale, high_update, constant_scale, finite_update]
    for action in reversed(actions) if reverse else actions:
        action()


_originals = None


def install():
    """Install after round12 runtime/hankel imports, before circuit building."""
    global _originals
    import border_circuit, central_circuit
    if _originals is None:
        _originals = (border_circuit.divide_locator, central_circuit.divide_locator)
    border_circuit.divide_locator = divide_locator
    central_circuit.divide_locator = divide_locator


def uninstall():
    global _originals
    if _originals is not None:
        import border_circuit, central_circuit
        border_circuit.divide_locator, central_circuit.divide_locator = _originals
        _originals = None


@contextmanager
def installed():
    install()
    try:
        yield
    finally:
        uninstall()
