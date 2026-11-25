"""Shared guarded D4 synthesis and projected phase for the compact shelf."""

from math import gcd

from qcompile.dqi.decoder import _multiply
from qcompile.dqi.field import GF4096
from qcompile.vendored.dqi_d4_compact import (
    _count_layout_failure,
    _flag,
    _masked_word,
    absorb_compact_pair,
    absorb_projected_outer,
    compact_tail_jet,
    extract_compact_heads,
)
from qcompile.vendored.dqi_d4_degree import odd_monic_conversion, projected_monic_scan
from qcompile.vendored.dqi_d4_mixed import xor_adjacent_outer_tail, xor_separated_outer_tail


def _scale_words(builder, reference, words, lead, *, reverse):
    inverse = reference.ar.inverse(builder, lead)
    factor, reciprocal = (lead, inverse) if reverse else (inverse, lead)
    for word in words:
        reference.scale_word(builder, word, factor, reciprocal)
    reference.ar.erase_inverse(builder, lead, inverse)
    builder.free(inverse)


def _xor_tail_seed(
    builder, reference, words, denominator, extraction, failures, *,
    targets=None, phase_masks=None, reverse=False, release_collapses=False,
):
    """Write the tail seed or repay its measured phase from the same products."""
    def chart_flags():
        return ([collapse for collapse, _, _ in extraction]
                + [chain["pole"] for _, _, chain in extraction if chain is not None])

    regular = _flag(builder, reference, [], chart_flags())
    if release_collapses:
        # A collapsed derivative inverts to the zero second head. All
        # other second heads remain nonzero under inversion and the
        # coordinate change. Recover the same flags after the solve.
        for index, (collapse, _, _) in enumerate(extraction):
            start = 4 * index + 2
            reference.clear_flag(builder, reference.combine(words[start:start + 2]), collapse)
    n0, wronskian = words[-2:]
    d0 = denominator
    heads = [words[i:i + 2] for i in range(0, 68, 2)]
    a, b, area = (builder.alloc_qubits(12) for _ in range(3))
    multiply = reference.ar.mul_xor0

    # Replay the root band (N36,N35,D35,D34)=(0,0,1,0)
    # into the tail band (a,c,b,d), keeping only the top (a,b)
    # and the determinant a*d+b*c of the two band rows.
    def transfer(undo=False):
        for low, high in reversed(heads) if undo else heads:
            if undo:
                multiply(builder, high, a, b)
                builder.swap(a, b)
            multiply(builder, a, b, area)
            builder.cx(high, low)
            reference.square12(builder, b)
            multiply(builder, low, b, area)
            reference.square12(builder, b, True)
            builder.cx(high, low)
            if not undo:
                builder.swap(a, b)
                multiply(builder, high, a, b)

    builder.x(b[0])
    transfer()
    product, determinant = (builder.alloc_qubits(12) for _ in range(2))
    # Eliminating the degree-34 root coordinate gives
    # det=d0*area+n0*b² and t=(d0²*a+b*W)/det. Build the
    # determinant as zero on mixed charts so inverse(0)=0
    # disables every regular output without a masked inverse.
    def xor_regular_product():
        with _masked_word(builder, n0, regular) as masked:
            multiply(builder, masked, b, product)

    def xor_determinant():
        with _masked_word(builder, d0, regular) as masked:
            multiply(builder, masked, area, determinant)
        multiply(builder, b, product, determinant)

    xor_regular_product()
    xor_determinant()
    singular = reference.zero_flag(builder, determinant)
    inverse = reference.ar.inverse(builder, determinant)
    if phase_masks is None:
        if targets is None:
            targets = [builder.alloc_qubits(12) for _ in range(3)]
        n1, n2, d1 = targets
        emit_product = multiply
    else:
        n1, n2, d1 = phase_masks
        emit_product = reference.ar.phase_product
    numerator, value = (builder.alloc_qubits(12) for _ in range(2))

    def xor_lead_numerator():
        reference.square12(builder, d0)
        multiply(builder, d0, a, numerator)
        reference.square12(builder, d0, True)
        multiply(builder, b, wronskian, numerator)

    def xor_slope_numerator():
        # n1=(W*area+n0*b*d0*a)/det also works when d0=0.
        multiply(builder, wronskian, area, numerator)
        multiply(builder, product, d0, value)
        multiply(builder, value, a, numerator)
        multiply(builder, product, d0, value)

    xor_lead_numerator()
    multiply(builder, numerator, inverse, value)
    emit_product(builder, a, value, n2)
    emit_product(builder, b, value, d1)
    multiply(builder, numerator, inverse, value)
    xor_lead_numerator()
    xor_slope_numerator()
    emit_product(builder, numerator, inverse, n1)
    xor_slope_numerator()
    builder.free(value)
    builder.free(numerator)
    reference.ar.erase_inverse(builder, determinant, inverse)
    builder.free(inverse)

    reciprocal = reference.ar.inverse(builder, d0)
    denominator_zero = reference.zero_flag(builder, d0)
    with _masked_word(builder, reciprocal, singular) as factor:
        emit_product(builder, wronskian, factor, n1)
    invalid_unit = _flag(builder, reference, [singular, denominator_zero], [])
    _count_layout_failure(builder, reference, n0, invalid_unit, failures, reverse=reverse, when_zero=True)
    _count_layout_failure(builder, reference, wronskian, invalid_unit, failures, reverse=reverse)
    _flag(builder, reference, [singular, denominator_zero], [], invalid_unit)
    reference.clear_flag(builder, d0, denominator_zero)
    reference.ar.erase_inverse(builder, d0, reciprocal)
    builder.free(reciprocal)
    reference.clear_flag(builder, determinant, singular)
    xor_determinant()
    xor_regular_product()
    transfer(True)
    builder.x(b[0])
    for word in (a, b, area, product, determinant):
        builder.free(word)
    if release_collapses:
        for index, (_, local, chain) in enumerate(extraction):
            start = 4 * index + 2
            collapse = reference.zero_flag(builder, reference.combine(words[start:start + 2]))
            extraction[index] = collapse, local, chain
    _flag(builder, reference, [], chart_flags(), regular)
    return targets


def _toggle_bound(builder, reference, first, evaluator, locator, failures, target, *, extra_ones=()):
    # Check degree 35 and 36 in N=q0*E+h0*D.
    second, top = evaluator[-2:]
    multiply = reference.ar.mul_xor0
    builder.cx(top, second)
    multiply(builder, first[0], locator[-1], second)
    multiply(builder, first[1], locator[-2], second)
    multiply(builder, first[1], locator[-1], top)
    upper_zero = reference.zero_flag(builder, top)
    lower_zero = reference.zero_flag(builder, [*second, *failures])
    ones = [upper_zero, lower_zero, *extra_ones]
    flag = _flag(builder, reference, ones, [])
    builder.cx(flag, target)
    _flag(builder, reference, ones, [], flag)
    reference.clear_flag(builder, [*second, *failures], lower_zero)
    reference.clear_flag(builder, top, upper_zero)
    multiply(builder, first[1], locator[-1], top)
    multiply(builder, first[1], locator[-2], second)
    multiply(builder, first[0], locator[-1], second)
    builder.cx(top, second)


def _multiply_padding(builder, reference, bank, enable, polynomial, *, reverse):
    """Conditionally multiply by a public monic polynomial in a fixed bank."""
    shift = len(polynomial) - 1
    terms = [(i, c) for i, c in enumerate(polynomial[:-1]) if c]

    def rotate():
        cycles = gcd(len(bank), shift)
        length = len(bank) // cycles
        for start in range(cycles):
            order = range(length - 1, 0, -1) if reverse else range(1, length)
            for index in order:
                builder.cswap(enable, bank[start], bank[(start + index * shift) % len(bank)])

    if not reverse:
        rotate()
    if terms:
        order = range(len(bank) - 1, shift - 1, -1) if reverse else range(shift, len(bank))
        for i in order:
            with _masked_word(builder, bank[i], enable) as source:
                for exponent, coefficient in terms:
                    reference.cx(builder, source, bank[i - shift + exponent], coefficient)
    if reverse:
        rotate()


def _pad_to_monic_degree(builder, reference, evaluator, locator):
    """Move a degree 21–34 locator to degree 35 with disjoint padding roots."""
    field = GF4096()
    factors = []
    coordinate = 34
    for quadratics in (4, 2, 1):
        polynomial = [1]
        for _ in range(quadratics):
            constant = reference.K ^ coordinate ^ field.mul(coordinate, coordinate)
            polynomial = _multiply(polynomial, [constant, 1, 1], field)
            coordinate += 2
        factors.append(polynomial)
    factors.append([0, 1])

    def padding_control(high, enable=None):
        if len(high) == 1:
            if enable is None:
                return reference.zero_flag(builder, high[0])
            reference.clear_flag(builder, high[0], enable)
            return enable
        flags = [reference.zero_flag(builder, word) for word in high]
        result = _flag(builder, reference, flags, [], enable)
        for word, flag in zip(high, flags, strict=True):
            reference.clear_flag(builder, word, flag)
        return result

    history = []
    for polynomial in factors:
        high = locator[1 - len(polynomial):]
        enable = padding_control(high)
        for bank in (evaluator, locator):
            _multiply_padding(builder, reference, bank, enable, polynomial, reverse=False)
        history.append((high, enable, polynomial))

    def undo():
        for high, enable, polynomial in reversed(history):
            for bank in (locator, evaluator):
                _multiply_padding(builder, reference, bank, enable, polynomial, reverse=True)
            padding_control(high, enable)

    return undo


def _zero_syndrome(builder, reference, words, target=None):
    chunks = [reference.combine(words[i:i + 4]) for i in range(0, len(words), 4)]
    zeroes = [reference.zero_flag(builder, chunk) for chunk in chunks]
    result = _flag(builder, reference, zeroes, [], target)
    for chunk, zero in zip(chunks, zeroes, strict=True):
        reference.clear_flag(builder, chunk, zero)
    return result


def emit_shared_projected_d4(
    builder, reference, converter, words, masks, *, on_coefficients=None, rejected=None, outer_poles=(),
):
    """Emit one compact shelf, one conversion and a guarded residual scan.

    A rejected input receives the shared projection phase only. If
    supplied, rejected is XORed on nonzero inputs without a residual
    scan. An exact decoder still needs a phase for those branches.
    The optional outer-pole pattern selects a guarded mixed-tail
    probe and its wider coefficient shelf.
    """
    if outer_poles not in ((), (0, 1), (0, 2)):
        raise ValueError("Unsupported outer-pole probe")
    mixed_solver = {(0, 1): xor_adjacent_outer_tail, (0, 2): xor_separated_outer_tail}.get(outer_poles)
    zero_input = _zero_syndrome(builder, reference, words) if rejected is not None else None
    mask_token = reference.baseline.project(builder, words, masks)
    reference.linear_words(builder, words, reference.matrix)
    extraction = extract_compact_heads(builder, reference, words, unit_first=True)
    denominator = compact_tail_jet(builder, reference, words, extraction, unit_first=True)
    # Up to 33 clipped pivots, 33 bad layout slots, and two tail failures.
    failures = builder.alloc_qubits(7)
    if mixed_solver is not None:
        degree = 3 if outer_poles == (0, 1) else 4
        tail = [builder.alloc_qubits(12) for _ in range(2 * degree - 1)]
        eligible = builder.alloc_qubits(1)[0]
        mixed_solver(builder, reference, words, denominator, extraction, tail, eligible)
        u, v = [words[-2], *tail[:degree]], [denominator, *tail[degree:]]
    else:
        eligible = None
        tail = _xor_tail_seed(
            builder, reference, words, denominator, extraction, failures, release_collapses=True,
        )
        assert tail is not None
        u, v = [words[-2], *tail[:2]], [denominator, tail[2]]
    phases = []
    history = []

    def fold(heads, a, b, coordinate, collapse, incoming, *, reverse=False):
        return absorb_compact_pair(builder, reference, heads, a, b, coordinate, collapse, incoming_pole=incoming,
                                   reverse=reverse, phase_masks=phases, zero_pivots=failures)

    for index in reversed(range(1, 17)):
        start = 4 * index
        heads = words[start:start + 2], words[start + 2:start + 4]
        collapse, _, chain = extraction[index]
        history.append((heads, u, v, 2 * index, collapse, chain["pole"]))
        u, v = fold(*history[-1])
    outer = (words[2:4], u, v, extraction[0][0])
    e, d = absorb_projected_outer(builder, reference, *outer, phase_masks=phases, zero_pivots=failures)
    certified = builder.alloc_qubits(1)[0]
    excess = reference.combine(e[35:] + d[36:]) if eligible is not None else None
    e, d = e[:35], d[:36]

    def toggle_certificate():
        if excess is None:
            _toggle_bound(builder, reference, words[:2], e, d, failures, certified)
        else:
            zero = reference.zero_flag(builder, excess)
            _toggle_bound(builder, reference, words[:2], e, d, failures, certified, extra_ones=(eligible, zero))
            reference.clear_flag(builder, excess, zero)

    toggle_certificate()
    if on_coefficients is not None:
        on_coefficients(e, d, certified)

    undo_padding = _pad_to_monic_degree(builder, reference, e, d)
    lead = d[-1]
    zero = reference.zero_flag(builder, lead)
    enabled = _flag(builder, reference, [certified], [zero])
    if zero_input is not None:
        builder.x([enabled, zero_input])
        builder.ccx(enabled, zero_input, rejected)
        builder.x([enabled, zero_input])
    builder.cx(zero, lead[0])
    payload = e + d[:-1]
    _scale_words(builder, reference, payload, lead, reverse=False)
    convert = odd_monic_conversion(converter)
    conversion = convert(builder, e, d[:-1])
    projected_monic_scan(builder, reference, e, d[:-1], masks, enable=enabled)
    convert(builder, e, d[:-1], token=conversion)
    _scale_words(builder, reference, payload, lead, reverse=True)
    builder.cx(zero, lead[0])
    _flag(builder, reference, [certified], [zero], enabled)
    reference.clear_flag(builder, lead, zero)
    undo_padding()
    toggle_certificate()
    builder.free(certified)
    absorb_projected_outer(builder, reference, *outer, reverse=True, phase_masks=phases, zero_pivots=failures)
    for row in reversed(history):
        fold(*row, reverse=True)
    if phases:
        raise ValueError("Shared D4 synthesis retained unpaid measurement phases")
    tail_masks = []
    for word in tail:
        mask = builder.alloc_bits(12)
        builder.hmr(word, mask)
        builder.free(word)
        tail_masks.append(mask)
    if mixed_solver is None:
        _xor_tail_seed(builder, reference, words, denominator, extraction, failures, reverse=True,
                       phase_masks=tail_masks, release_collapses=True)
    else:
        mixed_solver(builder, reference, words, denominator, extraction, tail_masks, eligible, phase=True)
        builder.free(eligible)
    for mask in tail_masks:
        builder.free(mask)
    builder.free(failures)
    compact_tail_jet(builder, reference, words, extraction, reverse=True, denominator=denominator, unit_first=True)
    extract_compact_heads(builder, reference, words, reverse=True, token=extraction, unit_first=True, replay_norms=True)
    reference.linear_words(builder, words, reference.matrix, True)
    reference.baseline.restore(builder, masks, mask_token)
    if zero_input is not None:
        _zero_syndrome(builder, reference, words, zero_input)
