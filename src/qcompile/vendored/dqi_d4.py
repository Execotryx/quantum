"""Ablation over SomeJoint D4, a4b5a8c288f17f8c09469820848d2d7c16e16044.

Upstream: https://www.kaggle.com/code/somejoint/quantum-circuits-22-75-local-gm-897-qubit-dqi
Paths: exp/r-main/stream/replay_erase.py and playbook/kit/decoder/final_decoder/decode.py.
2026-11-15: route selected ordinary groups through the existing homogeneous chain.
2026-11-15: emit the paired pole transfer in that chain's extension basis.
2026-11-15: select regular and pole pair transfers with a coherent chart bit.
"""

from collections.abc import Iterable
from contextlib import contextmanager
from itertools import permutations
from types import ModuleType


@contextmanager
def homogeneous_groups(module: ModuleType, groups: tuple[int, ...]):
    if len(set(groups)) != len(groups) or any(group not in range(8) for group in groups):
        raise ValueError("Ablation groups must be distinct ordinary D4 groups from 0 through 7")
    replay = module.replay_erase
    # Forward uses ref.extraction, while reverse uses the cloned
    # external_extraction with the replay-erase chain.
    scopes = (vars(replay.ref), replay.external_extraction.__globals__)
    originals = tuple(scope["EXTERNAL_HOMOGENEOUS"] for scope in scopes)
    try:
        for scope, original in zip(scopes, originals, strict=True):
            scope["EXTERNAL_HOMOGENEOUS"] = original.union(groups)
        yield
    finally:
        for scope, original in zip(scopes, originals, strict=True):
            scope["EXTERNAL_HOMOGENEOUS"] = original


def local_pole_jet(builder, reference, head, numerator, denominator, derivative, factor, coordinate, *, reverse=False):
    """Emit the paired transfer on one other external node's live projective jet.

    The branch has already been selected by the caller. The extension
    registers are disjoint, and factor is the nonzero value of the
    doubled node's quadratic at the target node.
    """
    if not factor:
        raise ValueError("The target must be a distinct external node")
    squared = reference.mul(factor, factor)
    if reverse:
        builder.swap(numerator, denominator)
        inverse = reference.inv(squared)
        reference.scalepair(builder, denominator, inverse)
        reference.scalepair(builder, derivative, inverse)
    reference.external_mul_head(builder, head, denominator, numerator, coordinate)
    _slope_product(builder, reference, head[1], denominator, derivative)
    if not reverse:
        reference.scalepair(builder, denominator, squared)
        reference.scalepair(builder, derivative, squared)
        builder.swap(numerator, denominator)


class _ControlledProduct:
    """Guard the rank-one nonlinear gates, leaving their conjugations intact."""

    def __init__(self, builder, control, scratch):
        self.builder = builder
        self.control = control
        self.scratch = scratch
        self.cx = builder.cx

    def ccx(self, a, b, target):
        self.builder.init_and(self.control, a, self.scratch)
        self.builder.ccx(self.scratch, b, target)
        self.builder.del_and(self.control, a, self.scratch)


class _ControlledLinear:
    """Guard every elementary gate of a pinned constant-field map."""

    def __init__(self, builder, control):
        self.builder = builder
        self.control = control

    def cx(self, source, target):
        self.builder.ccx(self.control, source, target)

    def swap(self, a, b):
        self.builder.cswap(self.control, a, b)


def _slope_product(builder, reference, slope, denominator, derivative):
    reference.external_square24(builder, denominator)
    for offset in (0, 12):
        reference.ar.mul_xor0(
            builder, slope, denominator[offset:offset + 12], derivative[offset:offset + 12],
        )
    reference.external_square24(builder, denominator, True)


def paired_external_jet(
    builder, reference, heads, chart, state, factor, coordinate, *, reverse=False,
):
    """Apply one doubled-node transfer at another node without reading chart."""
    if not factor:
        raise ValueError("The target must be a distinct external node")
    first, second = heads
    numerator, denominator, derivative = state
    squared = reference.mul(factor, factor)
    linear = _ControlledLinear(builder, chart)
    if len(numerator) == 12:
        scale_word = reference.scale

        def multiply_head(target_builder, head, source, target):
            reference.ar.mul_xor0(target_builder, head[0], source, target)

        def square(builder, word, undo=False):
            reference.square12(builder, word, undo)

        def first_slope():
            square(builder, denominator)
            reference.ar.mul_xor0(builder, first[1], denominator, derivative)
            square(builder, denominator, True)
    else:
        scale_word = reference.scalepair

        def multiply_head(target_builder, head, source, target):
            reference.external_mul_head(target_builder, head, source, target, coordinate)

        square = reference.external_square24

        def first_slope():
            _slope_product(builder, reference, first[1], denominator, derivative)

    def common():
        first_slope()
        multiply_head(builder, first, denominator, numerator)

    def regular():
        # The intermediate chart after the first head is S = N + h0 D.
        # The pair's derivative remainder is (h1 + q h1') * S².
        scratch = builder.alloc_qubits(1)[0]
        product = _ControlledProduct(builder, chart, scratch)
        scale = reference.inv(factor) if reverse else factor
        if reverse:
            scale_word(linear, numerator, scale)
            multiply_head(product, second, numerator, denominator)
            scale_word(linear, denominator, scale)

        reference.cx(builder, second[1], second[0], factor)
        square(builder, numerator)
        multiply_head(product, second, numerator, derivative)
        square(builder, numerator, True)
        reference.cx(builder, second[1], second[0], factor)

        if not reverse:
            scale_word(linear, denominator, scale)
            multiply_head(product, second, numerator, denominator)
            scale_word(linear, numerator, scale)
        builder.free(scratch)

    if reverse:
        builder.cswap(chart, numerator, denominator)
        scale_word(linear, denominator, reference.inv(squared))
    else:
        common()
        scale_word(builder, derivative, squared)

    builder.x(chart)
    regular()
    builder.x(chart)

    if reverse:
        scale_word(builder, derivative, reference.inv(squared))
        common()
    else:
        scale_word(linear, denominator, squared)
        builder.cswap(chart, numerator, denominator)


def paired_external_node_chain(
    builder, reference, words, group, charts, *,
    reverse=False, token=None, transport=paired_external_jet, scalar_replay=False, unit_transport=None,
    replay_norms=False,
):
    """Evaluate previous doubled-node heads with their retained live charts."""
    if len(charts) != group or not group:
        raise ValueError("The chain requires one chart per preceding external group")
    geometry = reference.groups[group]
    start = geometry["word"]
    numerator = reference.combine(words[start:start + 2])
    derivative = reference.combine(words[start + 2:start + 4])
    denominator = builder.alloc_qubits(24)
    builder.x(denominator[0])
    steps = [
        (
            (words[index * 4:index * 4 + 2], words[index * 4 + 2:index * 4 + 4]),
            chart,
            reference.ks[index * 2] ^ geometry["kap"],
        )
        for index, chart in enumerate(charts)
    ]

    def transfer(undo=False, scalar=False, unit=False, skip_first=False):
        indices = range(int(skip_first), len(steps))
        if undo:
            indices = reversed(indices)
        for i in indices:
            heads, chart, factor = steps[i]
            emit = unit_transport if unit and i == 0 and unit_transport is not None else transport
            emit(
                builder, reference, heads, chart, (numerator, denominator, None if scalar else derivative),
                factor, geometry["c"], reverse=undo,
            )

    if not reverse:
        transfer(unit=True)
        pole = reference.zero_flag(builder, denominator)
        builder.cswap(pole, numerator, denominator)
        norm = reference.external_normalize_paired(builder, numerator, denominator, derivative)
        gauge = builder.alloc_bits(24)
        builder.hmr(denominator, gauge)
        builder.free(denominator)
        return {"pole": pole, "norm": norm, "gauge": gauge}

    if token is None:
        raise ValueError("The reverse chain requires the original normalization token")
    pole = token["pole"]
    builder.cswap(pole, numerator, denominator)
    if unit_transport is None:
        transfer(undo=True)
        reciprocal, norm = reference.external_normalize_paired(
            builder, numerator, denominator, derivative, True, token["norm"],
        )
    else:
        transfer(undo=True, skip_first=True)
        heads, chart, factor = steps[0]
        reciprocal, norm = unit_transport(
            builder, reference, heads, chart, (numerator, denominator, derivative),
            factor, geometry["c"], reverse=True, normalize_token=token["norm"],
        )
    deferred_norm = None
    if replay_norms:
        # At entry D is the reciprocal gauge. Its norm is reciprocal,
        # and norm is the inverse of that word. Reclaim these registers
        # before transport and rebuild them from the recovered gauge.
        deferred_norm = builder.alloc_bits(12)
        builder.hmr(norm, deferred_norm)
        builder.free(norm)
        reference.ar._erase_norm(builder, denominator, reciprocal, reference.K)
        builder.free(reciprocal)
    inverse_mask = builder.alloc_bits(24)
    builder.hmr(denominator, inverse_mask)
    builder.free(denominator)

    # Recompute the forward gauge to repay both measured denominators.
    denominator = builder.alloc_qubits(24)
    builder.x(denominator[0])
    transfer(scalar=scalar_replay, unit=True)
    builder.cswap(pole, numerator, denominator)
    builder.cz(denominator, token["gauge"])
    builder.free(token["gauge"])
    if deferred_norm is not None:
        reference.ar._phase_norm(builder, denominator, deferred_norm, reference.K)
        builder.free(deferred_norm)
        reciprocal = builder.alloc_qubits(12)
        reference.norm_xor_noscratch(builder, denominator, reciprocal, reference.K)
        norm_mask = reference.inverse_stream_noscratch(builder, reciprocal)
        reference.ar._phase_norm(builder, denominator, norm_mask, reference.K)
        builder.free(norm_mask)
        norm = builder.alloc_qubits(12)
        reference.norm_xor_noscratch(builder, denominator, norm, reference.K)
    reference.external_inverse_phase_norm_pair(builder, denominator, inverse_mask, reciprocal, norm)
    builder.cswap(pole, numerator, denominator)
    reference.clear_flag(builder, denominator, pole)
    transfer(undo=True, scalar=scalar_replay, unit=True)
    builder.x(denominator[0])
    builder.free(denominator)


def paired_external_extraction(
    builder, reference, words, *, reverse=False, token=None, transport=paired_external_jet,
    scalar_replay=False, chart_state=None, local_chart=None, unit_transport=None, replay_norms=False,
):
    """Extract doubled external heads with a live bit for each local zero chart."""
    groups = reference.groups[:-1]
    if reverse and (token is None or len(token) != len(groups)):
        raise ValueError("The reverse extractor requires all forward chart tokens")
    history = list(token) if reverse and token is not None else []
    def charts():
        return [row[0] if chart_state is None else chart_state(row) for row in history]

    for group, geometry in reversed(list(enumerate(groups))) if reverse else enumerate(groups):
        start = geometry["word"]
        coordinate = geometry["c"]
        low, slope = words[start:start + 2]
        derivative = reference.combine(words[start + 2:start + 4])
        if reverse:
            chart, local, chain = history.pop()
            reference.cx(builder, words[start + 3], words[start + 2], coordinate)
            reference.inverse24_reverse209(builder, derivative, local, reference.K)
            reference.clear_flag(builder, derivative, chart)
            builder.cx(slope, derivative[:12])
            reference.cx(builder, slope, low, coordinate)
            if local_chart is not None and chain is not None:
                local_chart(builder, reference, reference.combine(words[start:start + 2]), derivative, group,
                            chain, reverse=True)
            if group:
                paired_external_node_chain(
                    builder, reference, words, group, charts(), reverse=True, token=chain,
                    transport=transport, scalar_replay=scalar_replay, unit_transport=unit_transport,
                    replay_norms=replay_norms,
                )
        else:
            chain = paired_external_node_chain(
                builder, reference, words, group, charts(), transport=transport, unit_transport=unit_transport,
            ) if group else None
            if local_chart is not None and chain is not None:
                local_chart(builder, reference, reference.combine(words[start:start + 2]), derivative, group, chain)
            reference.cx(builder, slope, low, coordinate)
            builder.cx(slope, derivative[:12])
            chart = reference.zero_flag(builder, derivative)
            local = reference.inverse24_forward190(builder, derivative, reference.K)
            reference.cx(builder, words[start + 3], words[start + 2], coordinate)
            history.append((chart, local, chain))
    return history


def paired_tail(builder, reference, words, charts, *, reverse=False, denominator=None,
                transport=paired_external_jet, unit_transport=None):
    """Evaluate the retained chart at zero without measuring the tail gauge."""
    if len(charts) != len(reference.groups) - 1:
        raise ValueError("The tail requires all external pair charts")
    if reverse and denominator is None:
        raise ValueError("The tail inverse requires its original denominator")
    if denominator is None:
        denominator = builder.alloc_qubits(12)
        builder.x(denominator[0])
    states = words[-2], denominator, words[-1]
    steps = list(enumerate(charts))
    for index, chart in reversed(steps) if reverse else steps:
        start = reference.groups[index]["word"]
        heads = words[start:start + 2], words[start + 2:start + 4]
        emit = unit_transport if index == 0 and unit_transport is not None else transport
        emit(builder, reference, heads, chart, states, reference.ks[2 * index], 0, reverse=reverse)
    if reverse:
        builder.x(denominator[0])
        builder.free(denominator)
    return denominator


def _scale_polynomial(builder, reference, coefficients, modulus, *, reverse):
    """Multiply modulo X^width by a constant polynomial with a nonzero constant."""
    shifts = [(offset, coefficient) for offset, coefficient in enumerate(modulus[1:], 1) if coefficient]
    constant = reference.inv(modulus[0]) if reverse else modulus[0]
    order = range(len(coefficients))
    for index in order if reverse else reversed(order):
        target = coefficients[index]
        if not reverse:
            reference.scale(builder, target, constant)
        for offset, coefficient in shifts:
            if index >= offset:
                reference.cx(builder, coefficients[index - offset], target, coefficient)
        if reverse:
            reference.scale(builder, target, constant)


def paired_polynomial_synthesis(builder, reference, heads, chart, state, kappa, *, reverse=False):
    """Apply a chart-selected paired transfer to two fixed-width coefficient banks."""
    if not kappa or len(state[0]) != len(state[1]):
        raise ValueError("Synthesis requires a nonzero node constant and equal polynomial banks")
    numerator, denominator = state
    linear = _ControlledLinear(builder, chart)
    scratch = builder.alloc_qubits(1)[0]
    product = _ControlledProduct(builder, chart, scratch)

    def swap_banks():
        for left, right in zip(numerator, denominator, strict=True):
            builder.cswap(chart, left, right)

    def fold(head, modulus):
        if reverse:
            swap_banks()
        else:
            _scale_polynomial(linear, reference, denominator, modulus, reverse=False)
        for shift, word in enumerate(head):
            for index in range(shift, len(denominator)):
                reference.ar.mul_xor0(product, word, numerator[index - shift], denominator[index])
        if reverse:
            _scale_polynomial(linear, reference, denominator, modulus, reverse=True)
        else:
            swap_banks()

    q = (kappa, 1, 1)
    squared = (reference.mul(kappa, kappa), 0, 1, 0, 1)

    def regular():
        builder.x(chart)
        for head in heads if reverse else reversed(heads):
            fold(head, q)
        builder.x(chart)

    if reverse:
        fold(heads[0], squared)
        regular()
    else:
        regular()
        fold(heads[0], squared)
    builder.free(scratch)


def _xor_linear_tail_slopes(builder, reference, jet, n1, d1):
    n, d, derivative = jet
    pole = reference.zero_flag(builder, d)
    builder.cswap(pole, n1, d1)
    builder.cswap(pole, n, d)
    reciprocal = reference.ar.inverse(builder, d)
    reference.ar.mul_xor0(builder, derivative, reciprocal, n1)
    reference.ar.erase_inverse(builder, d, reciprocal)
    builder.free(reciprocal)
    builder.cswap(pole, n, d)
    builder.cswap(pole, n1, d1)
    reference.clear_flag(builder, d, pole)


def _xor_regular_tail_correction(builder, reference, words, jet, charts, targets):
    """Replace the one-sided slopes when the all-regular system is nonsingular."""
    regular = reference.zero_flag(builder, charts)
    singular, mode = builder.alloc_qubits(2)
    correction = tuple(builder.alloc_qubits(12) for _ in range(3))
    heads = [words[index:index + 2] for index in range(0, 4 * len(charts), 2)]
    xor_regular_tail_coefficients(builder, reference, heads, jet, correction, singular)
    _xor_linear_tail_slopes(builder, reference, jet, correction[0], correction[2])
    builder.x(singular)
    builder.init_and(regular, singular, mode)
    for source, target in zip(correction, targets, strict=True):
        builder.ccx(mode, source, target)
    builder.del_and(regular, singular, mode)
    builder.x(singular)
    _xor_linear_tail_slopes(builder, reference, jet, correction[0], correction[2])
    xor_regular_tail_coefficients(builder, reference, heads, jet, correction, singular)
    for word in correction:
        builder.free(word)
    builder.free([singular, mode])
    reference.clear_flag(builder, charts, regular)


def synthesize_linear_tail(
    builder, reference, words, slopes, charts, width, *, reverse=False, banks=None, regular_solver=False,
):
    """Reconstruct polynomial banks with optional all-regular quadratic recovery.

    Mixed charts still use a one-sided linear seed. This diagnostic emitter
    does not certify that assumption or the coefficient width over all inputs.
    """
    if len(charts) != len(reference.groups) - 1 or width < 2:
        raise ValueError("Synthesis requires all pair charts and room for a linear tail")
    if reverse and banks is None:
        raise ValueError("The synthesis inverse requires the original banks")
    if banks is None:
        banks = tuple([builder.alloc_qubits(12) for _ in range(width)] for _ in range(2))
    nc, dc = banks
    n, d, _ = slopes
    if regular_solver and width < 3:
        raise ValueError("Regular recovery requires space for the quadratic coefficient")

    def seed_tail():
        builder.cx(n, nc[0])
        builder.cx(d, dc[0])
        _xor_linear_tail_slopes(builder, reference, slopes, nc[1], dc[1])
        if regular_solver:
            _xor_regular_tail_correction(builder, reference, words, slopes, charts, (nc[1], nc[2], dc[1]))

    if not reverse:
        seed_tail()
    steps = list(enumerate(charts))
    for index, chart in steps if reverse else reversed(steps):
        start = reference.groups[index]["word"]
        heads = words[start:start + 2], words[start + 2:start + 4]
        paired_polynomial_synthesis(builder, reference, heads, chart, banks, reference.ks[2 * index], reverse=reverse)
    if reverse:
        seed_tail()
        for word in nc + dc:
            builder.free(word)
    return banks


def _count_repeated_root(builder, reference, root, derivative, count):
    slope_zero = reference.zero_flag(builder, derivative)
    ladder = builder.alloc_qubits(len(count))
    builder.init_and(root, slope_zero, ladder[0])
    for i in range(1, len(count)):
        builder.init_and(ladder[i - 1], count[i - 1], ladder[i])
    for i in reversed(range(1, len(count))):
        builder.cx(ladder[i], count[i])
        builder.del_and(ladder[i - 1], count[i - 1], ladder[i])
    builder.cx(ladder[0], count[0])
    builder.del_and(root, slope_zero, ladder[0])
    builder.free(ladder)
    reference.clear_flag(builder, derivative, slope_zero)


def paired_residue_scan(
    builder, reference, banks, masks, positions: Iterable[int] = range(4095), *, repeated_root_count=None,
):
    """Apply residue phase from explicit coefficient banks and restore those banks."""
    positions = tuple(positions)
    if positions != tuple(sorted(set(positions))) or any(not 0 <= point < 4095 for point in positions):
        raise ValueError("Scan points must be distinct and increasing")
    numerator, denominator = banks
    n, d, derivative = (builder.alloc_qubits(12) for _ in range(3))
    mark = builder.alloc_bits(12)
    alpha = reference.gf.primitive_element
    previous = 0

    def scale(gap):
        step = reference.power(alpha, gap % 4095)
        multiplier = 1
        for a, b in zip(numerator[1:], denominator[1:], strict=True):
            multiplier = reference.mul(multiplier, step)
            reference.scale(builder, a, multiplier)
            reference.scale(builder, b, multiplier)

    def coefficients():
        for index, (a, b) in enumerate(zip(numerator, denominator, strict=True)):
            builder.cx(a, n)
            builder.cx(b, d)
            if index % 2:
                builder.cx(b, derivative)

    for point in positions:
        scale(point - previous)
        previous = point
        coefficients()
        root = reference.zero_flag(builder, d)
        if repeated_root_count is not None:
            _count_repeated_root(builder, reference, root, derivative, repeated_root_count)
        inv_slope = reference.ar.inverse(builder, derivative)
        symbol = builder.alloc_qubits(12)
        reference.ar.mul_xor0(builder, n, inv_slope, symbol)
        beta = reference.power(alpha, point)
        inverse = reference.inv(reference.eev(reference.P, beta))
        builder.bit_store(mark, False)
        for bit in range(12):
            for source in reference.ar.bits(reference.mul(inverse, 1 << bit)):
                builder.cx(masks[point][source], mark[bit])
        builder.ccz(root, symbol, mark)
        reference.ar.erase_product(builder, n, inv_slope, symbol)
        builder.free(symbol)
        reference.ar.erase_inverse(builder, derivative, inv_slope)
        builder.free(inv_slope)
        reference.clear_flag(builder, d, root)
        coefficients()
    scale(-previous)
    builder.free(mark)
    for register in (n, d, derivative):
        builder.free(register)


def xor_tail_system_solution(builder, reference, matrix, rhs, outputs, singular):
    """XOR the solution of a 3-by-3 GF(4096) system and its singular predicate.

    Matrices, right-hand sides and targets are disjoint live words. The
    singular branch contributes zeros because the inverse at zero is zero.
    """
    if len(matrix) != 3 or any(len(row) != 3 for row in matrix) or len(rhs) != 3 or len(outputs) != 3:
        raise ValueError("Expected a three-by-three tail system")
    det = builder.alloc_qubits(12)
    replacement = builder.alloc_qubits(12)
    partial = builder.alloc_qubits(12)
    xor_product = reference.ar.mul_xor0

    def xor_determinant(columns, target):
        for i, j, k in permutations(range(3)):
            a, b, c = columns[0][i], columns[1][j], columns[2][k]
            xor_product(builder, a, b, partial)
            xor_product(builder, partial, c, target)
            xor_product(builder, a, b, partial)

    columns = tuple(zip(*matrix, strict=True))
    xor_determinant(columns, det)
    reference.guarded.zero_toggle(builder, det, singular)
    inverse = reference.ar.inverse(builder, det)
    for col, output in enumerate(outputs):
        replaced = [rhs if index == col else words for index, words in enumerate(columns)]
        xor_determinant(replaced, replacement)
        xor_product(builder, replacement, inverse, output)
        xor_determinant(replaced, replacement)
    reference.ar.erase_inverse(builder, det, inverse)
    builder.free(inverse)
    xor_determinant(columns, det)
    for word in (det, replacement, partial):
        builder.free(word)


def xor_regular_tail_coefficients(builder, reference, heads, jet, outputs, singular):
    """Recover the three unknown tail coefficients for an all-regular chart.

    The output order is n1, n2, d1. The top-degree equations follow the
    numerator through every pair. This primitive does not handle pole
    chart bits or certify consistency for a different chart.
    """
    n0, d0, slope = jet
    columns = [[builder.alloc_qubits(12) for _ in range(4)] for _ in range(4)]

    def basis():
        for column, index in zip(columns, (1, 0, 2, 3), strict=True):
            builder.x(column[index][0])

    def transfer(reverse=False):
        for head in heads if reverse else reversed(heads):
            low, high = head
            for n_high, n_low, d_high, d_low in columns:
                if reverse:
                    builder.swap(n_high, d_high)
                    builder.swap(n_low, d_low)
                else:
                    builder.cx(d_high, d_low)
                reference.ar.mul_xor0(builder, high, n_low, d_low)
                reference.ar.mul_xor0(builder, low, n_high, d_low)
                reference.ar.mul_xor0(builder, high, n_high, d_high)
                if reverse:
                    builder.cx(d_high, d_low)
                else:
                    builder.swap(n_high, d_high)
                    builder.swap(n_low, d_low)

    basis()
    transfer()
    zero, high_rhs, low_rhs = (builder.alloc_qubits(12) for _ in range(3))
    reference.ar.mul_xor0(builder, columns[3][0], d0, high_rhs)
    reference.ar.mul_xor0(builder, columns[3][1], d0, low_rhs)
    matrix = (
        (d0, zero, n0),
        tuple(column[1] for column in columns[:3]),
        tuple(column[0] for column in columns[:3]),
    )
    xor_tail_system_solution(builder, reference, matrix, (slope, low_rhs, high_rhs), outputs, singular)
    reference.ar.mul_xor0(builder, columns[3][1], d0, low_rhs)
    reference.ar.mul_xor0(builder, columns[3][0], d0, high_rhs)
    for word in (zero, high_rhs, low_rhs):
        builder.free(word)
    transfer(reverse=True)
    basis()
    for column in columns:
        for word in column:
            builder.free(word)
