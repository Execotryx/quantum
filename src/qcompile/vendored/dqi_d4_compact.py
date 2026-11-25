"""D4 local-pole absorption using the existing head and coefficient wires.

The extension arithmetic is from the admitted SomeJoint D4 source,
revision a4b5a8c288f17f8c09469820848d2d7c16e16044.
"""

from contextlib import contextmanager
from functools import lru_cache
from math import gcd

from qcompile.dqi.decoder import _divide
from qcompile.dqi.field import GF4096
from qcompile.vendored.dqi_d4 import _slope_product, paired_external_extraction, paired_tail
from qcompile.vendored.dqi_d4_leading import aligned_head_product, aligned_quadratic


@lru_cache(maxsize=64)
def monomial_coordinates(count: int, kappa: int, order: int) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Expand monomials in the basis (1,X,q,Xq,q²,Xq²,...) up to order."""
    field = GF4096()
    modulus = [kappa, 1, 1]
    columns = []
    for exponent in range(count):
        quotient = [0] * exponent + [1]
        column = []
        for _ in range(order):
            quotient, remainder = _divide(quotient, modulus, field)
            column.extend(remainder + [0] * (2 - len(remainder)))
        columns.append(tuple((index, value) for index, value in enumerate(column + quotient) if value))
    return tuple(columns)


@lru_cache(maxsize=64)
def quotient_interpolation(count: int, width: int, kappa: int, order: int, inverse_rows):
    """Compose interpolation with the quotient coordinates used by the fold."""
    field = GF4096()
    rows = monomial_coordinates(count, kappa, order)
    outputs = []
    for point in range(count):
        column = [0] * (width - 2)
        for row, weights in zip(rows, inverse_rows, strict=True):
            for slot, value in row:
                if slot >= 2:
                    column[slot - 2] ^= field.mul(value, weights[point])
        outputs.append(tuple(column))
    return tuple(outputs)


def absorb_local_pole(builder, reference, first_head, second_head, u, v, coordinate: int, *, reverse=False):
    """Map (h,0,U,V) to (N,D) on the finite-first-visit pole chart.

    D aliases U, and N aliases h, the zero second head, and V in
    ascending coefficient order. U mod q must be nonzero in every
    admitted input, where q = X² + X + K + coordinate² + coordinate.
    """
    return _absorb(builder, reference, first_head, second_head, u, v, coordinate, reverse=reverse), u


@contextmanager
def _masked_word(builder, word, enable):
    masked = builder.alloc_qubits(len(word))
    for source, target in zip(word, masked, strict=True):
        builder.init_and(enable, source, target)
    yield masked
    for source, target in zip(word, masked, strict=True):
        builder.del_and(enable, source, target)
    builder.free(masked)


def affine_denominator_jet(builder, reference, state, coordinate, enable, translate=None):
    """XOR (X+translate)*N into D and N² into the derivative on enable.

    Use None for the scalar node X=0 and a base coordinate for X=c+Y.
    The optional live translation bit selects the affine constant 0 or 1.
    The map is its own inverse and preserves the projective scale.
    """
    n, d, derivative = state
    with _masked_word(builder, n, enable) as source:
        if coordinate is not None:
            # (c+Y)(a+bY) = (c*a+K*b)+Y*(a+(c+1)*b).
            a, b = source[:12], source[12:]
            reference.cx(builder, a, d[:12], coordinate)
            reference.cx(builder, b, d[:12], reference.K)
            builder.cx(a, d[12:])
            reference.cx(builder, b, d[12:], coordinate ^ 1)
        if translate is not None:
            builder.ccx(translate, source, d)
        if derivative is not None:
            square = reference.square12 if coordinate is None else reference.external_square24
            square(builder, source)
            builder.cx(source, derivative)
            square(builder, source, True)


def affine_denominator_banks(builder, reference, numerator, denominator, enable, translate=None):
    """Apply the same self-inverse shear to degree-bounded coefficient banks."""
    if len(denominator) != len(numerator) + 1:
        raise ValueError("The denominator bank must have exactly one extra degree slot")
    for i, word in enumerate(numerator):
        if translate is None:
            builder.ccx(enable, word, denominator[i + 1])
        else:
            with _masked_word(builder, word, enable) as source:
                builder.cx(source, denominator[i + 1])
                builder.ccx(translate, source, denominator[i])


def escape_normalized_affine_chart(builder, reference, numerator, derivative, coordinate, *, token=None):
    """Repair a nonzero collapsed local head before the ordinary pair split.

    The input jet has denominator one. Retain the returned flags both for
    later-node transports and for undoing this normalized local change.
    """
    singular = reference.einv(coordinate | 4096)

    def toggle_translation(target):
        builder.flip_if_equal(numerator, singular, target=target)

    def make_enable(target=None):
        builder.cx(numerator[12:], derivative[:12])
        collapsed = reference.zero_flag(builder, derivative)
        zero_head = reference.zero_flag(builder, numerator)
        target = _flag(builder, reference, [collapsed], [zero_head], target)
        reference.clear_flag(builder, numerator, zero_head)
        reference.clear_flag(builder, derivative, collapsed)
        builder.cx(numerator[12:], derivative[:12])
        return target

    if token is None:
        enable = make_enable()
        translation = builder.alloc_qubits(1)[0]
        toggle_translation(translation)
    else:
        enable, translation = token[:2]

    def denominator_for(slope):
        denominator = builder.alloc_qubits(24)
        builder.x(denominator[0])
        affine_denominator_jet(
            builder, reference, (numerator, denominator, slope), coordinate, enable, translation,
        )
        return denominator

    denominator = denominator_for(derivative)
    if token is None:
        normalization = reference.external_normalize_paired(builder, numerator, denominator, derivative)
        gauge = builder.alloc_bits(24)
        builder.hmr(denominator, gauge)
        builder.free(denominator)
        return enable, translation, normalization, gauge

    normalization, gauge = token[2:]
    reciprocal, norm = reference.external_normalize_paired(
        builder, numerator, denominator, derivative, True, normalization,
    )
    inverse_mask = builder.alloc_bits(24)
    builder.hmr(denominator, inverse_mask)
    builder.free(denominator)
    denominator = denominator_for(None)
    builder.cz(denominator, gauge)
    builder.free(gauge)
    reference.external_inverse_phase_norm_pair(builder, denominator, inverse_mask, reciprocal, norm)
    builder.free(inverse_mask)
    affine_denominator_jet(
        builder, reference, (numerator, denominator, None), coordinate, enable, translation,
    )
    builder.x(denominator[0])
    builder.free(denominator)
    toggle_translation(translation)
    builder.free(translation)
    make_enable(enable)
    return None


def compact_pair_jet(
    builder, reference, heads, state, factor: int, coordinate: int, incoming_pole, collapse, *,
    reverse=False, unit=False, normalize_token=None,
):
    """Transport the finite chart to another node, with an optional derivative."""
    if not factor:
        raise ValueError("Pair transfer requires a distinct target node")
    if unit and incoming_pole is not None:
        raise ValueError("The initialized denominator is only available on the first chart")
    first, second = heads
    n, d, derivative = state
    base = len(n) == 12
    if normalize_token is not None and (not reverse or not unit or base or derivative is None):
        raise ValueError("Deferred first additions require an external jet at inverse normalization")
    square = reference.square12 if base else reference.external_square24
    scale = reference.scale if base else reference.scalepair
    squared = reference.mul(factor, factor)

    def product(head, source, target):
        if base:
            reference.ar.mul_xor0(builder, head[0], source, target)
        else:
            reference.external_mul_head(builder, head, source, target, coordinate)

    def first_head():
        if unit:
            if base:
                builder.cx(first[0], n)
            else:
                reference.cx(builder, first[1], first[0], coordinate)
                builder.cx(reference.combine(first), n)
                reference.cx(builder, first[1], first[0], coordinate)
            if derivative is not None:
                builder.cx(first[1], derivative[:12])
                builder.cx(collapse, derivative[0])
            for bit in reference.ar.bits(factor):
                builder.cx(collapse, n[bit])
            return
        # On collapse this head is h0+q. Its value at the target
        # changes by factor and its derivative changes by one.
        if derivative is not None:
            builder.cx(collapse, first[1][0])
            if base:
                square(builder, d)
                reference.ar.mul_xor0(builder, first[1], d, derivative)
                square(builder, d, True)
            else:
                _slope_product(builder, reference, first[1], d, derivative)
            builder.cx(collapse, first[1][0])
        for bit in reference.ar.bits(factor):
            builder.cx(collapse, first[0][bit])
        product(first, d, n)
        for bit in reference.ar.bits(factor):
            builder.cx(collapse, first[0][bit])

    def second_derivative():
        if derivative is not None:
            reference.cx(builder, second[1], second[0], factor)
            square(builder, n)
            product(second, n, derivative)
            square(builder, n, True)
            reference.cx(builder, second[1], second[0], factor)

    builder.cx(collapse, second[0][0])
    normalization = None
    if reverse:
        scale(builder, n, reference.inv(factor))
        if unit and normalize_token is None:
            # D=q+h1*N. Both product operands are still live, so erase
            # the product in the phase frame and recreate the unit word.
            for bit in reference.ar.bits(factor):
                builder.x(d[bit])
            mask = builder.alloc_bits(len(d))
            builder.hmr(d, mask)
            if base:
                reference.ar.phase_product(builder, second[0], n, mask)
            else:
                reference.cx(builder, second[1], second[0], coordinate)
                reference.folds.phase_product24(builder, reference.combine(second), n, mask, reference.K)
                reference.cx(builder, second[1], second[0], coordinate)
            builder.free(mask)
            builder.x(d[0])
        else:
            product(second, n, d)
            scale(builder, d, reference.inv(factor))
        second_derivative()
        if derivative is not None:
            scale(builder, derivative, reference.inv(squared))
        if normalize_token is not None:
            # Before normalization the starting D is the reciprocal gauge.
            # h0*D, q*D and their derivative terms become simple additions
            # only after division by D and D² has restored the input jet.
            normalization = reference.external_normalize_paired(
                builder, n, d, derivative, True, normalize_token,
            )
        first_head()
        if incoming_pole is not None:
            builder.cswap(incoming_pole, n, d)
    else:
        if incoming_pole is not None:
            builder.cswap(incoming_pole, n, d)
        first_head()
        if derivative is not None:
            scale(builder, derivative, squared)
        second_derivative()
        scale(builder, d, factor)
        product(second, n, d)
        scale(builder, n, factor)
    builder.cx(collapse, second[0][0])
    return normalization


def _chart_state(row):
    collapse, _, chain = row
    return (None if chain is None else chain["pole"]), collapse


def _affine_chart_state(row):
    return (*_chart_state(row), None if row[2] is None else row[2].get("affine"))


def _chart_transport(builder, reference, heads, chart, state, factor, coordinate, *, reverse=False):
    incoming_pole, collapse = chart
    compact_pair_jet(builder, reference, heads, state, factor, coordinate, incoming_pole, collapse, reverse=reverse)


def _affine_chart_transport(builder, reference, heads, chart, state, factor, coordinate, *, reverse=False):
    incoming, collapse, affine = chart
    if affine is None:
        return _chart_transport(builder, reference, heads, (incoming, collapse), state, factor, coordinate,
                                reverse=reverse)
    enable, translation = affine[:2]
    n, d, _ = state
    jet_node = None if len(n) == 12 else coordinate

    if reverse:
        compact_pair_jet(builder, reference, heads, state, factor, coordinate, None, collapse, reverse=True)
        affine_denominator_jet(builder, reference, state, jet_node, enable, translation)
        builder.cswap(incoming, n, d)
    else:
        builder.cswap(incoming, n, d)
        affine_denominator_jet(builder, reference, state, jet_node, enable, translation)
        compact_pair_jet(builder, reference, heads, state, factor, coordinate, None, collapse)


def _unit_chart_transport(builder, reference, heads, chart, state, factor, coordinate, *,
                          reverse=False, normalize_token=None):
    incoming, collapse = chart[:2]
    return compact_pair_jet(builder, reference, heads, state, factor, coordinate, incoming, collapse,
                            reverse=reverse, unit=True, normalize_token=normalize_token)


def extract_compact_heads(builder, reference, words, *, reverse=False, token=None, scalar_replay=True,
                          affine_group=None, unit_first=False, replay_norms=False):
    """Extract and restore the doubled-node heads with both charts intact."""
    if reverse and token is not None:
        recorded = next((i for i, row in enumerate(token) if row[2] is not None and "affine" in row[2]), None)
        if affine_group is not None and affine_group != recorded:
            raise ValueError("Affine group differs from its forward extraction token")
        affine_group = recorded
    if affine_group is not None and not 1 <= affine_group <= 16:
        raise ValueError("The affine escape requires a noninitial external group")

    def prepare_local(b, ref, n, w, group, chain, *, reverse=False):
        if group == affine_group:
            if reverse:
                escape_normalized_affine_chart(b, ref, n, w, 2 * group, token=chain["affine"])
            else:
                chain["affine"] = escape_normalized_affine_chart(b, ref, n, w, 2 * group)

    affine = affine_group is not None
    return paired_external_extraction(
        builder, reference, words, reverse=reverse, token=token,
        transport=_affine_chart_transport if affine else _chart_transport,
        scalar_replay=scalar_replay, chart_state=_affine_chart_state if affine else _chart_state,
        local_chart=prepare_local if affine else None,
        unit_transport=_unit_chart_transport if unit_first else None,
        replay_norms=replay_norms,
    )


def compact_tail_jet(builder, reference, words, token, *, reverse=False, denominator=None, unit_first=False):
    """Evaluate the same chart sequence at the final scalar node."""
    affine = any(row[2] is not None and "affine" in row[2] for row in token)
    chart_state = _affine_chart_state if affine else _chart_state
    return paired_tail(
        builder, reference, words, [chart_state(row) for row in token],
        reverse=reverse, denominator=denominator, transport=_affine_chart_transport if affine else _chart_transport,
        unit_transport=_unit_chart_transport if unit_first else None,
    )


def _flag(builder, reference, ones, zeros, flag=None):
    controls = [*ones, *zeros]
    # The admitted zero-flag eraser expects at least three operands.
    if len(controls) == 2:
        builder.x(zeros)
        if flag is None:
            flag = builder.alloc_qubits(1)[0]
            builder.init_and(*controls, flag)
        else:
            builder.del_and(*controls, flag)
            builder.free(flag)
        builder.x(zeros)
        return flag
    builder.x(ones)
    if flag is None:
        flag = reference.zero_flag(builder, controls)
    else:
        reference.clear_flag(builder, controls, flag)
    builder.x(ones)
    return flag


def xor_terminated_compact_tail(builder, reference, words, charts, target):
    """Toggle when a full D4 chart suffix certifies the unit tail (1, 0).

    The first incoming flag is absent. The first two words of each four-word
    group hold the first head. The observable output is the predicate alone.
    """
    if len(words) != 68 or len(charts) != 17 or charts[0][0] is not None:
        raise ValueError("Expected complete D4 heads with a finite first chart")

    def predicate(ones, zeros, flag=None):
        return _flag(builder, reference, ones, zeros, flag)

    def suffix_flag(group, next_flag, flag=None):
        incoming, collapse = charts[group]
        head = reference.combine(words[4 * group:4 * group + 2])
        zero_head = reference.zero_flag(builder, head)
        required = [incoming, collapse, zero_head]
        if next_flag is not None:
            required.append(next_flag)
        result = predicate(required, [], flag)
        reference.clear_flag(builder, head, zero_head)
        return result

    # For k suffix folds the signed comparison is 1-2k plus the prefix
    # adjustments to 35-2j. The range [-31,33] fits signed seven bits.
    counter = builder.alloc_qubits(7)
    builder.x(counter[0])
    suffix = {}
    next_flag = None
    for group in range(16, 0, -1):
        next_flag = suffix_flag(group, next_flag)
        suffix[group] = next_flag

    def accumulate(group, *, reverse=False):
        incoming, collapse = charts[group]
        past_collapse = charts[group - 1][1]
        in_suffix = suffix[group]
        base = predicate([incoming], [in_suffix])
        finite_collapse = predicate([collapse], [incoming])
        extra = predicate([past_collapse], [finite_collapse, in_suffix])
        increase, decrease = (builder.isub, builder.iadd) if reverse else (builder.iadd, builder.isub)
        increase(1, target=counter, control=base)
        increase(1, target=counter, control=extra)
        decrease(1, target=counter[1:], control=in_suffix)
        predicate([past_collapse], [finite_collapse, in_suffix], extra)
        predicate([collapse], [incoming], finite_collapse)
        predicate([incoming], [in_suffix], base)

    for group in range(16, 0, -1):
        accumulate(group)
    builder.cx(counter[-1], target)
    for group in range(1, 17):
        accumulate(group, reverse=True)
        suffix_flag(group, suffix.get(group + 1), suffix.pop(group))
    builder.x(counter[0])
    builder.free(counter)


def _unit_tail_pattern(charts, group):
    ones = [charts[group][1], charts[-1][1]]
    zeros = [incoming for incoming, _ in charts if incoming is not None]
    zeros.extend(collapse for i, (_, collapse) in enumerate(charts) if i not in (group, 16))
    return ones, zeros


def _unit_tail_flag(builder, reference, charts, jet, group, target=None):
    n0, d0, wronskian = jet
    ones, zeros = _unit_tail_pattern(charts, group)
    pattern = _flag(builder, reference, ones, zeros)
    jet_zeroes = reference.combine([d0, wronskian])
    good_jet = reference.zero_flag(builder, jet_zeroes)
    zero_n = reference.zero_flag(builder, n0)
    result = _flag(builder, reference, [pattern, good_jet], [zero_n], target)
    reference.clear_flag(builder, n0, zero_n)
    reference.clear_flag(builder, jet_zeroes, good_jet)
    _flag(builder, reference, ones, zeros, pattern)
    return result


def xor_unit_tail_certificate(builder, reference, charts, jet, group, target):
    """Toggle for the certified finite-intermediate and terminal collapse chart."""
    if len(charts) != 17 or charts[0][0] is not None or not 1 <= group <= 15:
        raise ValueError("Expected full D4 charts and a noninitial, nonterminal group")
    flag = _unit_tail_flag(builder, reference, charts, jet, group)
    builder.cx(flag, target)
    _unit_tail_flag(builder, reference, charts, jet, group, flag)


def xor_unit_tail_degree_certificate(builder, reference, charts, group, first, evaluator, locator, layout_ok, target):
    """Check a projected unit-tail reconstruction against the external degree bound."""
    if (len(evaluator) != 32 or len(locator) != 33 or len(charts) != 17 or charts[0][0] is not None
            or not 1 <= group <= 15):
        raise ValueError("Expected the tight projected unit-tail banks and an interior collapse")
    # N=q0*E+h0*D has degree at most 33. If the top coefficient
    # vanishes, the root cross-product has degree strictly below 68.
    high = evaluator[-1]
    reference.ar.mul_xor0(builder, first[1], locator[-1], high)
    bounded = reference.zero_flag(builder, high)
    ones, zeros = _unit_tail_pattern(charts, group)
    ones.extend((bounded, layout_ok))
    valid = _flag(builder, reference, ones, zeros)
    builder.cx(valid, target)
    _flag(builder, reference, ones, zeros, valid)
    reference.clear_flag(builder, high, bounded)
    reference.ar.mul_xor0(builder, first[1], locator[-1], high)


def xor_unit_tail_degree31_certificate(
    builder, reference, charts, group, evaluator, locator, layout_ok, zero_pivots, target,
):
    """Qualify the tight unit-tail layout for the degree-31 scan."""
    if (len(evaluator) != 32 or len(locator) != 33 or len(charts) != 17 or charts[0][0] is not None
            or not 1 <= group <= 15):
        raise ValueError("Expected the tight projected unit-tail banks and an interior collapse")
    # These two high coefficients imply deg(N)<=32 and deg(D)<=31,
    # giving a cross product of degree at most 67 against the original pair.
    excess = [*evaluator[31], *locator[32], *zero_pivots]
    high_zero = reference.zero_flag(builder, excess)
    lead_zero = reference.zero_flag(builder, locator[31])
    ones, zeros = _unit_tail_pattern(charts, group)
    ones.extend((high_zero, layout_ok))
    zeros.append(lead_zero)
    valid = _flag(builder, reference, ones, zeros)
    builder.cx(valid, target)
    _flag(builder, reference, ones, zeros, valid)
    reference.clear_flag(builder, locator[31], lead_zero)
    reference.clear_flag(builder, excess, high_zero)


def xor_incoming_degree_certificate(
    builder, reference, charts, group, first, evaluator, locator, discarded, zero_pivots, target, *, tail_zero=None,
):
    """Qualify a single incoming pole with an otherwise regular chain."""
    degree = len(evaluator)
    if (degree not in (32, 33) or len(locator) != degree + 1 or len(discarded) != 2
            or len(charts) != 17 or not 1 <= group <= 14):
        raise ValueError("Expected the compact degree-32 or degree-33 single-pole layout")
    # N = q0*E + h0*D. Require deg(N)<=32 so the candidate cross
    # product with the original degree-(34,35) bounds is below 68.
    top = evaluator[-1]
    next_top = evaluator[-2]
    multiply = reference.ar.mul_xor0
    if degree == 33:
        builder.cx(top, next_top)
        multiply(builder, first[0], locator[-1], next_top)
        multiply(builder, first[1], locator[-2], next_top)
    multiply(builder, first[1], locator[-1], top)
    required_zero = [*top]
    if degree == 33:
        required_zero.extend(next_top)
    required_zero.extend(zero_pivots)
    bounded = reference.zero_flag(builder, required_zero)
    spill_wires = reference.combine(discarded)
    spills_zero = reference.zero_flag(builder, spill_wires)
    lead_zero = reference.zero_flag(builder, locator[-1])
    incoming = charts[group][0]
    zeros = [pole for i, (pole, _) in enumerate(charts) if i != group and pole is not None]
    zeros.extend(collapse for _, collapse in charts)
    zeros.append(lead_zero)
    if tail_zero is not None:
        zeros.append(tail_zero)
    ones = [incoming, bounded, spills_zero]
    valid = _flag(builder, reference, ones, zeros)
    builder.cx(valid, target)
    _flag(builder, reference, ones, zeros, valid)
    reference.clear_flag(builder, locator[-1], lead_zero)
    reference.clear_flag(builder, spill_wires, spills_zero)
    reference.clear_flag(builder, required_zero, bounded)
    multiply(builder, first[1], locator[-1], top)
    if degree == 33:
        multiply(builder, first[1], locator[-2], next_top)
        multiply(builder, first[0], locator[-1], next_top)
        builder.cx(top, next_top)


def xor_unit_tail_preshear(builder, reference, words, charts, jet, group, output, eligible):
    """Recover the affine quotient for one finite collapse and a terminal collapse.

    The selected group must be the only collapse before the final group.
    Incoming swaps are excluded. A matching unit jet and the root bounds
    certify the reconstruction. The quotient and qualification bit are XORed.
    """
    if len(words) != 68 or len(charts) != 17 or charts[0][0] is not None or not 1 <= group <= 15:
        raise ValueError("Expected complete heads and one noninitial, nonterminal escape group")
    n0, d0, wronskian = jet
    banks = tuple([builder.alloc_qubits(12) for _ in range(4)] for _ in range(2))

    def seed():
        builder.cx(words[65], banks[0][0])
        builder.cx(words[64], banks[0][1])
        builder.x(banks[1][0][0])

    seed()
    a, b = banks
    steps = []
    for index in range(15, group, -1):
        kappa = reference.ks[2 * index]
        for offset in (2, 0):
            head = words[4 * index + offset:4 * index + offset + 2][::-1]
            aligned_quadratic(builder, reference, b, kappa)
            aligned_head_product(builder, reference, head, a, b)
            steps.append((a, b, head, kappa))
            a, b = b, a

    positives = [charts[group][1], charts[-1][1]]
    negatives = [incoming for incoming, _ in charts if incoming is not None]
    negatives.extend(collapse for i, (_, collapse) in enumerate(charts) if i not in (group, 16))
    pattern = _flag(builder, reference, positives, negatives)
    jet_zeroes = reference.combine([d0, wronskian])
    top_zeroes = reference.combine(b[:2])
    good_jet = reference.zero_flag(builder, jet_zeroes)
    good_top = reference.zero_flag(builder, top_zeroes)
    zero_n = reference.zero_flag(builder, n0)
    zero_u = reference.zero_flag(builder, a[0])
    valid = _flag(builder, reference, [pattern, good_jet, good_top], [zero_n, zero_u])
    builder.cx(valid, eligible)

    # At the selected collapsed fold D=U+qV and N=h*D+q²V.
    # The two highest V coefficients are zero on the admitted degree
    # chart. Thus qV leaves D's leading word alone and changes its second.
    inverse = reference.ar.inverse(builder, a[0])
    # These words are zero on eligible inputs. For all other inputs
    # they are arbitrary XOR targets and must be restored by multiplication.
    slope, intercept = b[:2]
    multiply = reference.ar.mul_xor0
    builder.cx(b[2], a[1])
    multiply(builder, b[2], inverse, slope)
    multiply(builder, slope, a[1], b[3])
    multiply(builder, b[3], inverse, intercept)
    for index, (term, target) in enumerate(zip((intercept, slope), output, strict=True)):
        head = words[4 * group + index]
        builder.cx(head, term)
        builder.ccx(valid, term, target)
        builder.cx(head, term)
    multiply(builder, b[3], inverse, intercept)
    multiply(builder, slope, a[1], b[3])
    multiply(builder, b[2], inverse, slope)
    builder.cx(b[2], a[1])
    reference.ar.erase_inverse(builder, a[0], inverse)
    builder.free(inverse)

    _flag(builder, reference, [pattern, good_jet, good_top], [zero_n, zero_u], valid)
    reference.clear_flag(builder, a[0], zero_u)
    reference.clear_flag(builder, n0, zero_n)
    reference.clear_flag(builder, top_zeroes, good_top)
    reference.clear_flag(builder, jet_zeroes, good_jet)
    _flag(builder, reference, positives, negatives, pattern)
    for source, target, head, kappa in reversed(steps):
        aligned_head_product(builder, reference, head, source, target)
        aligned_quadratic(builder, reference, target, kappa, reverse=True)
    seed()
    for bank in banks:
        for word in bank:
            builder.free(word)


def xor_aligned_history_overflow(builder, reference, charts, capacity, target):
    """Toggle when the cumulative aligned shifts exceed the spill capacity."""
    if len(charts) != 17 or charts[0][0] is not None or not 0 <= capacity <= 66:
        raise ValueError("Expected full D4 charts and a capacity from zero to 66")

    counter = builder.alloc_qubits(8)
    offset = [wire for i, wire in enumerate(counter) if (-capacity >> i) & 1]
    builder.x(offset)
    builder.iadd(1, target=counter, control=charts[0][1])

    def accumulate(group, operation):
        incoming, collapse = charts[group]
        previous = charts[group - 1][1]
        # Absolute gap change = (previous XOR collapse) + 2 incoming
        # + 2 (incoming AND previous AND collapse).
        changed = builder.alloc_qubits(1)[0]
        builder.cx(previous, changed)
        builder.cx(collapse, changed)
        double = _flag(builder, reference, [incoming, previous, collapse], [])
        operation(1, target=counter, control=changed)
        operation(1, target=counter[1:], control=incoming)
        operation(1, target=counter[1:], control=double)
        _flag(builder, reference, [incoming, previous, collapse], [], double)
        builder.cx(collapse, changed)
        builder.cx(previous, changed)
        builder.free(changed)

    for group in range(1, 17):
        accumulate(group, builder.iadd)
    # Counter = shifts - capacity - 1. A nonnegative counter means overflow.
    builder.x(counter[-1])
    builder.cx(counter[-1], target)
    builder.x(counter[-1])
    for group in range(16, 0, -1):
        accumulate(group, builder.isub)
    builder.isub(1, target=counter, control=charts[0][1])
    builder.x(offset)
    builder.free(counter)


def replay_aligned_chart(builder, reference, heads, banks, history, kappa, incoming, previous, collapse,
                         *, reverse=False):
    """Update one leading row with a shared LIFO spill bank.

    Use absent incoming and previous flags for the initial chart. There
    must be enough zero capacity at the end of history for the selected
    shift. Reverse the factors in the opposite order to clear history.
    """
    a, b = banks
    if len(a) != len(b) or len(a) < 4 or len(history) < 4 or (incoming is None) != (previous is None):
        raise ValueError("Expected matching bands, a full spill bank, and both or neither chart inputs")

    chart_flags = []

    def flag(ones, zeros):
        target = _flag(builder, reference, ones, zeros)
        chart_flags.append((ones, zeros, target))
        return target

    def bank_swap():
        if incoming is not None:
            builder.cswap(incoming, reference.combine(a), reference.combine(b))

    def shift(bank, control, undo=False, distance=1):
        cycles = gcd(len(bank), distance)
        positions = range(1, len(bank) // cycles)
        for pivot in range(cycles):
            for i in reversed(positions) if undo else positions:
                other = (pivot + i * distance) % len(bank)
                if control is None:
                    builder.swap(bank[pivot], bank[other])
                else:
                    builder.cswap(control, bank[pivot], bank[other])

    if incoming is None:
        a_shift = None
        head_offset = collapse
        b_controls = ((None, 1), (collapse, 1))
    else:
        a_shift = flag([previous], [incoming, collapse])
        incoming_previous = flag([incoming, previous], [])
        finite_previous = flag([previous], [incoming])
        b_extra = flag([collapse], [finite_previous])
        head_offset = builder.alloc_qubits(1)[0]
        builder.cx(collapse, head_offset)
        builder.cx(a_shift, head_offset)
        b_controls = ((incoming, 2), (incoming_previous, 1), (b_extra, 1))

    def shift_b(undo=False):
        for control, distance in reversed(b_controls) if undo else b_controls:
            shift([*b, *history], control, undo, distance)

    def first_product():
        h0, _ = heads
        top = builder.alloc_qubits(12)
        head = [h0[1], h0[0], top]
        shift(head, head_offset)
        for word, coefficient in zip(head, (1, 1, kappa), strict=True):
            for bit in range(12):
                if coefficient >> bit & 1:
                    builder.cx(collapse, word[bit])
        aligned_head_product(builder, reference, head, a, b)
        for word, coefficient in zip(head, (1, 1, kappa), strict=True):
            for bit in range(12):
                if coefficient >> bit & 1:
                    builder.cx(collapse, word[bit])
        shift(head, head_offset, True)
        builder.free(top)

    def second_product():
        _, h1 = heads
        builder.cx(collapse, h1[1][0])
        aligned_head_product(builder, reference, h1[::-1], b, a)
        builder.cx(collapse, h1[1][0])

    if reverse:
        aligned_quadratic(builder, reference, b, kappa, reverse=True)
        second_product()
        if a_shift is not None:
            shift([*a, *history], a_shift, True)
        aligned_quadratic(builder, reference, a, kappa, reverse=True)
        first_product()
        shift_b(True)
        bank_swap()
    else:
        bank_swap()
        shift_b()
        first_product()
        aligned_quadratic(builder, reference, a, kappa)
        if a_shift is not None:
            shift([*a, *history], a_shift)
        second_product()
        aligned_quadratic(builder, reference, b, kappa)

    if incoming is not None:
        builder.cx(a_shift, head_offset)
        builder.cx(collapse, head_offset)
        builder.free(head_offset)
    for ones, zeros, target in reversed(chart_flags):
        _flag(builder, reference, ones, zeros, target)


def xor_monic_basis_coordinates(builder, reference, coordinates, leading, outputs, invalid):
    """Normalize basis weights before materializing the reconstructed polynomials."""
    words = list(zip(coordinates, leading, outputs, strict=True))
    if len(words) != 3:
        raise ValueError("A full-weight D4 basis requires three coordinates")
    scale = builder.alloc_qubits(12)
    for coordinate, coefficient, _ in words:
        reference.ar.mul_xor0(builder, coordinate, coefficient, scale)
    reference.guarded.zero_toggle(builder, scale, invalid)
    reciprocal = reference.ar.inverse(builder, scale)
    for coordinate, _, output in words:
        reference.ar.mul_xor0(builder, coordinate, reciprocal, output)
    reference.ar.erase_inverse(builder, scale, reciprocal)
    builder.free(reciprocal)
    for coordinate, coefficient, _ in words:
        reference.ar.mul_xor0(builder, coordinate, coefficient, scale)
    builder.free(scale)


def _count_zero_pivot(builder, count, control, *, reverse):
    """Conditionally increment the bounded pivot count, or undo it."""
    if reverse:
        builder.x(count)
    carry = [control]
    for bit in count[:-1]:
        extra = builder.alloc_qubits(1)[0]
        builder.init_and(carry[-1], bit, extra)
        carry.append(extra)
    for index in range(len(count) - 1, 0, -1):
        builder.cx(carry[index], count[index])
        builder.del_and(carry[index - 1], count[index - 1], carry[index])
    builder.free(carry[1:])
    builder.cx(control, count[0])
    if reverse:
        builder.x(count)


def _count_layout_failure(builder, reference, word, branch, count, *, reverse, when_zero=False):
    """Count a violated word constraint on a live chart."""
    if branch is None or count is None:
        return
    zero = reference.zero_flag(builder, word)
    if not when_zero:
        builder.x(zero)
    bad = builder.alloc_qubits(1)[0]
    builder.init_and(branch, zero, bad)
    _count_zero_pivot(builder, count, bad, reverse=reverse)
    builder.del_and(branch, zero, bad)
    builder.free(bad)
    if not when_zero:
        builder.x(zero)
    reference.clear_flag(builder, word, zero)


def _absorb(builder, reference, head_words, middle, u, v, coordinate, *, reverse, omit_top_slope=False,
            phase_masks=None, zero_pivots=None, add_quadratic=None):
    """Overwrite head, middle and V with (h + add_quadratic*q)*U + q^order*V."""
    needed = len(u) if omit_top_slope else len(u) + 1
    if add_quadratic is not None and needed < len(v) + 2 + len(middle):
        needed += 1
    if len(head_words) != 2 or len(middle) not in (0, 2) or not u or needed > len(v) + 2 + len(middle):
        raise ValueError("Fold exceeds its supplied coefficient layout")
    numerator = [*head_words, *middle, *v]
    order = 1 + len(middle) // 2
    kappa = reference.K ^ reference.mul(coordinate, coordinate) ^ coordinate
    kappa_squared = reference.mul(kappa, kappa)
    remainder_columns = monomial_coordinates(len(u), kappa, 1)
    old = reference.folds.old

    def expand_quotient(length, degree, middle_offset, constant):
        # Higher slots are the quotient by the fixed monic factor. Updating lower slots in
        # ascending order preserves each source until its last use.
        shifts = reversed(range(length)) if reverse else range(length)
        for index in shifts:
            source = numerator[index + degree]
            reference.cx(builder, source, numerator[index], constant)
            builder.cx(source, numerator[index + middle_offset])

    def expand():
        stages = [(len(v), 2, 1, kappa)] if order == 1 else [(2, 2, 1, kappa), (len(v), 4, 2, kappa_squared)]
        for stage in reversed(stages) if reverse else stages:
            expand_quotient(*stage)

    def add_product():
        evaluation, inverse = old.base.vandermonde(needed)
        weights = quotient_interpolation(needed, len(numerator), kappa, order, tuple(map(tuple, inverse)))
        target = numerator[2:]
        for point, column in enumerate(weights):
            bit_positions = () if add_quadratic is None else tuple(
                reference.ar.bits(reference.mul(point, point) ^ point ^ kappa)
            )
            for bit in bit_positions:
                builder.cx(add_quadratic, head_words[0][bit])
            old.rank_affine(builder, head_words, [1, point], u, evaluation[point][:len(u)], target, column)
            for bit in bit_positions:
                builder.cx(add_quadratic, head_words[0][bit])

    def xor_factor(factor):
        # The constant and linear terms are already in the two residue
        # slots. Expose U mod q in those slots and restore U after scaling.
        for source, column in zip(u[2:], remainder_columns[2:], strict=True):
            for slot, value in column:
                if slot < 2:
                    reference.cx(builder, source, factor[slot], value)

    def scale_head():
        factor = list(u[:2])
        if len(u) == 1:
            factor.append(builder.alloc_qubits(12))
        xor_factor(factor)
        # The source's GF24 arithmetic uses Y²+Y+K, where X=Y+coordinate.
        reference.cx(builder, factor[1], factor[0], coordinate)
        reference.cx(builder, head_words[1], head_words[0], coordinate)
        operand = reference.combine(factor)
        head = reference.combine(head_words)
        zero = reference.zero_flag(builder, operand) if zero_pivots is not None else None
        if zero is not None:
            builder.cx(zero, operand[0])
            _count_zero_pivot(builder, zero_pivots, zero, reverse=reverse)
        if phase_masks is None:
            if reverse:
                inverse_mask = reference.inverse24_forward190(builder, operand, reference.K)
                mask = reference.folds.multiply_forward99(builder, head, operand, reference.K)
                reference.inverse24_reverse209(builder, operand, inverse_mask, reference.K)
                reference.folds.phase_product24(builder, head, operand, mask, reference.K)
            else:
                mask = reference.folds.multiply_forward99(builder, head, operand, reference.K)
                inverse_mask = reference.inverse24_forward190(builder, operand, reference.K)
                reference.folds.phase_product24(builder, head, operand, mask, reference.K)
                reference.inverse24_reverse209(builder, operand, inverse_mask, reference.K)
            builder.free(mask)
        elif reverse:
            reference.folds.divide_lowwidth369(builder, head, operand, reference.K)
            mask = phase_masks.pop()
            builder.cz(head, mask)
            builder.free(mask)
        else:
            phase_masks.append(reference.folds.multiply_forward99(builder, head, operand, reference.K))
        if zero is not None:
            builder.cx(zero, operand[0])
            reference.clear_flag(builder, operand, zero)
        reference.cx(builder, head_words[1], head_words[0], coordinate)
        reference.cx(builder, factor[1], factor[0], coordinate)
        xor_factor(factor)
        if len(u) == 1:
            builder.free(factor[1])

    if reverse:
        expand()
        scale_head()
        add_product()
    else:
        add_product()
        scale_head()
        expand()
    return numerator


def absorb_compact_pair(
    builder, reference, heads, u, v, coordinate: int, collapse, *,
    incoming_pole=None, reverse=False, phase_masks=None, zero_pivots=None,
):
    """Use two finite folds and a conditional shear for a collapsed pair.

    U mod q is nonzero. On the finite chart h1 is nonzero, and the
    highest U slot is zero when U has two extra slots. On the collapsed
    chart h1 is zero and U uses the shear gauge U=U_original+q*V.
    V=0 includes exact termination. If U has only one extra slot, the
    highest V coefficient must be zero on the collapsed chart.
    Pass collapse=None for a known finite chart. Both pivots stay finite.
    An optional phase-mask stack defers repayment to the inverse.
    With a supplied zero_pivots counter, a zero pivot acts as one for
    scaling only and is counted. The counter must fit all guarded folds.
    Incoming-pole orientation requires the numerator's excess slots to
    be zero on that chart before the banks can exchange prefixes.
    """
    # With a one-slot difference both full head products fit. A collapsed
    # branch additionally needs the top D word to vanish before qD is added.
    tight = len(u) == len(v) + 1
    if not tight and len(u) != len(v) + 2:
        raise ValueError("Shared compact layout needs one or two more U slots than V slots")
    first, second = heads
    numerator, denominator = [*first, *u], [*second, *v]
    def incoming_check():
        for word in numerator[len(denominator):]:
            _count_layout_failure(builder, reference, word, incoming_pole, zero_pivots, reverse=reverse)

    def collapse_check():
        if tight and v:
            _count_layout_failure(builder, reference, v[-1], collapse, zero_pivots, reverse=reverse)

    if reverse:
        incoming_check()
        if incoming_pole is not None:
            builder.cswap(incoming_pole, reference.combine(numerator[:len(denominator)]),
                          reference.combine(denominator))
        _absorb(builder, reference, first, (), denominator, u, coordinate, reverse=True, phase_masks=phase_masks,
                zero_pivots=zero_pivots, add_quadratic=collapse)
        _absorb(builder, reference, second, (), u, v, coordinate,
                reverse=True, omit_top_slope=not tight, phase_masks=phase_masks, zero_pivots=zero_pivots)
        if collapse is not None:
            builder.cx(collapse, second[0][0])
        collapse_check()
    else:
        collapse_check()
        if collapse is not None:
            builder.cx(collapse, second[0][0])
        _absorb(builder, reference, second, (), u, v, coordinate,
                reverse=False, omit_top_slope=not tight, phase_masks=phase_masks, zero_pivots=zero_pivots)
        _absorb(builder, reference, first, (), denominator, u, coordinate, reverse=False, phase_masks=phase_masks,
                zero_pivots=zero_pivots, add_quadratic=collapse)
        incoming_check()
        if incoming_pole is not None:
            builder.cswap(incoming_pole, reference.combine(numerator[:len(denominator)]),
                          reference.combine(denominator))
    return numerator, denominator


def absorb_incoming_regular_pair(
    builder, reference, heads, u, v, coordinate, *, reverse=False, phase_masks=None, zero_pivots=None,
):
    """Invert the regular pair after an incoming first-head pole.

    The reciprocal chart has first head zero. With its two zero slots
    the original denominator is qU; the second head absorbs into V
    to give the original numerator h1*U + qV. Nonzero first-head
    words would still round-trip but invalidate this interpretation.
    """
    first, second = heads
    if len(first) != 2:
        raise ValueError("An incoming pair needs two first-head slots")
    denominator = [*first, *u]
    kappa = reference.K ^ reference.mul(coordinate, coordinate) ^ coordinate

    def multiply_quadratic():
        indices = reversed(range(len(u))) if reverse else range(len(u))
        for index in indices:
            source = u[index]
            reference.cx(builder, source, denominator[index], kappa)
            builder.cx(source, denominator[index + 1])

    if reverse:
        multiply_quadratic()
    numerator = _absorb(builder, reference, second, (), u, v, coordinate,
                        reverse=reverse, phase_masks=phase_masks, zero_pivots=zero_pivots)
    if not reverse:
        multiply_quadratic()
    return numerator, denominator


def absorb_projected_outer(builder, reference, second, u, v, collapse, *, reverse=False, phase_masks=None,
                           zero_pivots=None):
    """Omit the first quadratic fold and produce the locator and its evaluator.

    At the first external node the incoming denominator has no extension
    root. The input layout and second-head promises match the shared fold.
    The evaluator is (N + h0*D)/q0 and the locator is D, so the scan must
    use Pscan = P/q0 with the original projected masks.
    """
    tight = len(u) == len(v) + 1
    if not tight and len(u) != len(v) + 2:
        raise ValueError("Projected outer fold requires one or two extra numerator slots")
    locator = [*second, *v]

    def unshear_evaluator():
        if collapse is not None:
            for word, target in zip(locator[:len(u)], u, strict=True):
                builder.ccx(collapse, word, target)

    def collapse_check():
        if tight and v:
            _count_layout_failure(builder, reference, v[-1], collapse, zero_pivots, reverse=reverse)

    if reverse:
        unshear_evaluator()
        _absorb(builder, reference, second, (), u, v, 0, reverse=True, omit_top_slope=not tight,
                phase_masks=phase_masks, zero_pivots=zero_pivots)
        if collapse is not None:
            builder.cx(collapse, second[0][0])
        collapse_check()
    else:
        collapse_check()
        if collapse is not None:
            builder.cx(collapse, second[0][0])
        _absorb(builder, reference, second, (), u, v, 0, reverse=False, omit_top_slope=not tight,
                phase_masks=phase_masks, zero_pivots=zero_pivots)
        unshear_evaluator()
    return u, locator
