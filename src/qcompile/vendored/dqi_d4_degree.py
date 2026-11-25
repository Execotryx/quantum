"""Degree-parametric monic conversion and projected scan for admitted D4."""

from inspect import getclosurevars


def odd_monic_conversion(converter):
    """Adapt the admitted streaming converter's monic core for odd degrees."""
    scope = getclosurevars(converter).nonlocals["core"].__globals__
    old, bezout = scope["old"], scope["_bez_monic"]

    def convert(builder, evaluator, locator, *, token=None, history_scratch=None):
        degree = len(locator)
        if len(evaluator) != degree or degree < 5 or not degree % 2:
            raise ValueError("Expected equal banks with an odd implicit monic degree of at least five")
        reverse = token is not None
        if token is None:
            token = {"a": {}, "q": {}, "heads": {}, "_short_monic": True}
            for key in ("gap_flags", "given_gap", "incoming_gap", "return_mask", "returned_gap", "held_gap"):
                token[key] = {}

        old.frob(builder, locator, 2048)
        old.frob(builder, evaluator, 2048)
        even, odd = locator[::2], locator[1::2]
        u, w, top = evaluator[1::2], evaluator[:-1:2], evaluator[-1]
        multiply = old.ar.mul_xor0
        if reverse:
            for i in range(degree - 1):
                builder.swap(evaluator[i], evaluator[i + 1])
            old.hankel(builder, locator[1:], evaluator[:-1], True)
            for i in range(0, degree - 1, 2):
                builder.swap(evaluator[i], evaluator[i + 1])
            for value, target in zip(even[1:], w, strict=True):
                multiply(builder, value, target, top)
            bezout(builder, odd, even, [u, w], True, history_scratch, token)
            for value, target in zip(odd, w, strict=True):
                multiply(builder, top, value, target)
        else:
            for value, target in zip(odd, w, strict=True):
                multiply(builder, top, value, target)
            bezout(builder, odd, even, [u, w], False, history_scratch, token)
            for value, target in zip(even[1:], w, strict=True):
                multiply(builder, value, target, top)
            for i in range(0, degree - 1, 2):
                builder.swap(evaluator[i], evaluator[i + 1])
            old.hankel(builder, locator[1:], evaluator[:-1])
            for i in reversed(range(degree - 1)):
                builder.swap(evaluator[i], evaluator[i + 1])

        old.frob(builder, evaluator, 2)
        old.frob(builder, locator, 2)
        if reverse and any(token[key] for key in ("a", "q", "heads")):
            raise ValueError("Monic converter retained unpaid measurement terms")
        return None if reverse else token

    return convert


def projected_monic_scan(builder, reference, evaluator, locator, masks, *, enable=None):
    """Apply the admitted projected-scan recurrence at the supplied monic degree."""
    degree = len(locator)
    if len(evaluator) != degree or len(masks) != 4095:
        raise ValueError("Expected equal coefficient banks and a complete DQI mask bank")
    alpha = reference.gf.primitive_element
    powers = [reference.power(alpha, k) for k in range(1, degree)]
    skipped = frozenset(reference.baseline.SELECTED)
    beta, lead = 1, 1
    lead_step = reference.power(alpha, degree)
    mask = builder.alloc_bits(12)
    enabled_root = builder.alloc_qubits(1)[0] if enable is not None else None

    def accumulate():
        for a, d in zip(evaluator[1:], locator[1:], strict=True):
            builder.cx(a, evaluator[0])
            builder.cx(d, locator[0])
        builder.gf2_iadd(lead, target=locator[0])

    for position in range(4095):
        if position not in skipped:
            accumulate()
            ladder = reference.zero_hold(builder, locator[0])
            value = 0
            for coefficient in reversed(reference.Pscan):
                value = reference.mul(value, beta) ^ coefficient
            inverse = reference.inv(reference.mul(beta, value))
            if not inverse:
                raise ValueError("Projected scan encountered a zero public scale")
            builder.bit_store(mask, False)
            for bit in range(12):
                for source in reference.ar.bits(reference.mul(inverse, 1 << bit)):
                    builder.cx(masks[position][source], mask[bit])
            if enabled_root is None:
                builder.ccz(ladder[-1], evaluator[0], mask)
            else:
                builder.init_and(enable, ladder[-1], enabled_root)
                builder.ccz(enabled_root, evaluator[0], mask)
                builder.del_and(enable, ladder[-1], enabled_root)
            reference.zero_free(builder, locator[0], ladder)
            accumulate()
        for a, d, power in zip(evaluator[1:], locator[1:], powers, strict=True):
            reference.scale(builder, a, power)
            reference.scale(builder, d, power)
        beta = reference.mul(beta, alpha)
        lead = reference.mul(lead, lead_step)
    builder.free(mask)
    if enabled_root is not None:
        builder.free(enabled_root)
