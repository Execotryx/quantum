"""Tail recovery for outer collapse prefixes followed by regular D4 pairs."""

from qcompile.vendored.dqi_d4 import xor_tail_system_solution
from qcompile.vendored.dqi_d4_compact import _flag, _masked_word


def _transfer_band(builder, reference, words, u, v, first_head, *, reverse=False):
    """Apply the regular suffix to two descending coefficient bands."""
    multiply = reference.ar.mul_xor0
    heads = range(first_head, 34)
    a, b = reference.combine(u), reference.combine(v)
    for head in reversed(heads) if reverse else heads:
        low, high = words[2 * head:2 * head + 2]
        kappa = reference.ks[head]
        if not reverse:
            builder.swap(a, b)
        else:
            for i in range(len(v) - 1, 0, -1):
                builder.cx(v[i - 1], v[i])
                if i >= 2:
                    reference.cx(builder, v[i - 2], v[i], kappa)
        for i in range(len(v)):
            multiply(builder, high, u[i], v[i])
            if i:
                multiply(builder, low, u[i - 1], v[i])
        if reverse:
            builder.swap(a, b)
        else:
            for i in range(1, len(v)):
                builder.cx(v[i - 1], v[i])
                if i >= 2:
                    reference.cx(builder, v[i - 2], v[i], kappa)


def xor_adjacent_outer_tail(
    builder, reference, words, denominator, extraction, targets, eligible, *, phase=False,
):
    """XOR (n1,n2,n3,d1,d2), or pay the same products into HMR masks."""
    collapse = [flag for flag, _, _ in extraction]
    incoming = [chain["pole"] for _, _, chain in extraction if chain is not None]
    chart = _flag(builder, reference, collapse[:2], collapse[2:] + incoming)
    u, v = ([builder.alloc_qubits(12) for _ in range(4)] for _ in range(2))
    constant, slope = words[:2]
    multiply = reference.ar.mul_xor0
    emit_product = reference.ar.phase_product if phase else multiply

    def toggle_direction():
        # The V31 root direction after the two collapses. V32=0.
        # In descending degree, U starts at 33 and V starts at 32.
        builder.x(u[0][0])
        builder.x(u[1][0])
        builder.x(v[1][0])
        builder.cx(slope, u[1])
        builder.cx(constant, u[2])
        reference.square12(builder, slope)
        builder.cx(slope, u[2])
        reference.square12(builder, slope, True)
        for bit in reference.ar.bits(reference.ks[2]):
            builder.x(u[2][bit])

    toggle_direction()
    _transfer_band(builder, reference, words, u, v, 4)
    n0, wronskian = words[-2:]
    a, b = u[0], v[0]
    value_row, jet_row = ([builder.alloc_qubits(12) for _ in range(3)] for _ in range(2))
    rhs_value = builder.alloc_qubits(12)

    def xor_equations():
        # The remaining directions are shifts of the first. An
        # independent U30 coefficient affects only n0 and V[-1],
        # with coefficients a,b. Eliminate it using b*n0+a*V[-1].
        multiply(builder, b, n0, rhs_value)
        for j in range(3):
            multiply(builder, b, u[3 - j], value_row[j])
            multiply(builder, a, v[3 - j], value_row[j])
            multiply(builder, denominator, u[2 - j], jet_row[j])
            if j < 2:
                multiply(builder, n0, v[1 - j], jet_row[j])

    xor_equations()
    matrix = (value_row, v[2::-1], jet_row)
    rhs = (rhs_value, denominator, wronskian)
    weights = [builder.alloc_qubits(12) for _ in range(3)]
    singular = builder.alloc_qubits(1)[0]
    xor_tail_system_solution(builder, reference, matrix, rhs, weights, singular)
    active = _flag(builder, reference, [chart], [singular])
    builder.cx(active, eligible)
    views = ((u, 2), (u, 1), (u, 0), (v, 1), (v, 0))
    for offset, weight in enumerate(weights):
        with _masked_word(builder, weight, active) as source:
            for (bank, index), target in zip(views, targets, strict=True):
                if index >= offset:
                    emit_product(builder, source, bank[index - offset], target)
    _flag(builder, reference, [chart], [singular], active)
    xor_tail_system_solution(builder, reference, matrix, rhs, weights, singular)
    builder.free(singular)
    for word in weights:
        builder.free(word)
    xor_equations()
    for word in [*value_row, *jet_row, rhs_value]:
        builder.free(word)
    _transfer_band(builder, reference, words, u, v, 4, reverse=True)
    toggle_direction()
    for word in u + v:
        builder.free(word)
    _flag(builder, reference, collapse[:2], collapse[2:] + incoming, chart)


def _with_solution(builder, reference, rows, consume):
    """Solve a live augmented system, use its solution and erase the solve."""
    size = len(rows)
    multiply = reference.ar.mul_xor0
    combined = [reference.combine(row) for row in rows]
    factor = builder.alloc_qubits(12)
    swaps = []

    def pivot_flag(k, row, flag=None):
        pivot, candidate = rows[k][k], rows[row][k]
        pivot_zero = reference.zero_flag(builder, pivot)
        candidate_zero = reference.zero_flag(builder, candidate)
        result = _flag(builder, reference, [pivot_zero], [candidate_zero], flag)
        reference.clear_flag(builder, candidate, candidate_zero)
        reference.clear_flag(builder, pivot, pivot_zero)
        return result

    def eliminate(k):
        if k + 1 == size:
            return
        pivot = rows[k][k]
        inverse = reference.ar.inverse(builder, pivot)
        for row in rows[k + 1:]:
            multiply(builder, row[k], inverse, factor)
            for source, target in zip(rows[k][k + 1:], row[k + 1:], strict=True):
                multiply(builder, factor, source, target)
            multiply(builder, row[k], inverse, factor)
        reference.ar.erase_inverse(builder, pivot, inverse)
        builder.free(inverse)

    for k in range(size):
        selected = []
        for row in range(k + 1, size):
            flag = pivot_flag(k, row)
            builder.cswap(flag, combined[k], combined[row])
            selected.append((row, flag))
        swaps.append(selected)
        eliminate(k)

    singular = [reference.zero_flag(builder, row[k]) for k, row in enumerate(rows)]
    solution = [builder.alloc_qubits(12) for _ in rows]

    def substitute(k):
        row = rows[k]
        pivot = row[k]
        builder.cx(row[-1], factor)
        for value, coefficient in zip(solution[k + 1:], row[k + 1:-1], strict=True):
            multiply(builder, value, coefficient, factor)
        inverse = reference.ar.inverse(builder, pivot)
        multiply(builder, factor, inverse, solution[k])
        reference.ar.erase_inverse(builder, pivot, inverse)
        builder.free(inverse)
        for value, coefficient in zip(solution[k + 1:], row[k + 1:-1], strict=True):
            multiply(builder, value, coefficient, factor)
        builder.cx(row[-1], factor)

    for k in reversed(range(size)):
        substitute(k)
    consume(solution, singular)
    for k in range(size):
        substitute(k)
    for k, word in enumerate(solution):
        builder.free(word)
        reference.clear_flag(builder, rows[k][k], singular[k])
    for k in reversed(range(size)):
        eliminate(k)
        for row, flag in reversed(swaps[k]):
            builder.cswap(flag, combined[k], combined[row])
            pivot_flag(k, row, flag)
    builder.free(factor)


def _separated_direction(builder, reference, words, v, *, reverse=False):
    """Compute the short V/U series for a collapse–regular–collapse prefix."""
    c0, s0 = words[:2]
    c3, s3 = words[6:8]
    c4, s4 = words[8:10]
    k1, k2 = reference.ks[2], reference.ks[4]
    p = [builder.alloc_qubits(12) for _ in range(4)]
    g = [s3, *(builder.alloc_qubits(12) for _ in range(3))]
    square_sum = builder.alloc_qubits(12)
    multiply = reference.ar.mul_xor0

    def toggle_public(word, value):
        for bit in reference.ar.bits(value):
            builder.x(word[bit])

    def xor_p():
        multiply(builder, s3, s4, p[0])
        multiply(builder, s3, c4, p[1])
        multiply(builder, c3, s4, p[1])
        multiply(builder, c3, c4, p[2])
        toggle_public(p[0], 1)
        toggle_public(p[1], 1)
        toggle_public(p[2], k1)

    def xor_g():
        builder.cx(c3, g[1])
        builder.cx(p[0], g[1])
        for word in (s3, p[1], p[0], s0):
            builder.cx(word, g[2])
        for word in (c3, p[2], p[1], square_sum):
            builder.cx(word, g[3])
        reference.cx(builder, p[0], g[3], k2)
        multiply(builder, s0, s4, g[3])

    def xor_correction():
        multiply(builder, s0, s4, p[2])
        multiply(builder, s0, c4, p[3])
        multiply(builder, square_sum, s4, p[3])

    def xor_square_sum():
        builder.cx(s0, square_sum)
        builder.cx(c0, square_sum)
        reference.square12(builder, s0)
        builder.cx(s0, square_sum)
        reference.square12(builder, s0, True)

    xor_square_sum()
    xor_p()
    xor_g()
    xor_correction()
    inverse = reference.ar.inverse(builder, s3)
    for i in reversed(range(4)) if reverse else range(4):
        for j in range(1, i + 1):
            multiply(builder, g[j], v[i - j], p[i])
        multiply(builder, p[i], inverse, v[i])
        for j in range(1, i + 1):
            multiply(builder, g[j], v[i - j], p[i])
    reference.ar.erase_inverse(builder, s3, inverse)
    builder.free(inverse)
    xor_correction()
    xor_g()
    xor_p()
    xor_square_sum()
    for word in p + g[1:] + [square_sum]:
        builder.free(word)


def xor_separated_outer_tail(
    builder, reference, words, denominator, extraction, targets, eligible, *, phase=False,
):
    """XOR the degree-(4,3) tail for outer poles at groups 0 and 2."""
    collapse = [flag for flag, _, _ in extraction]
    incoming = [chain["pole"] for _, _, chain in extraction if chain is not None]
    required = [collapse[0], collapse[2]]
    excluded = [collapse[1], *collapse[3:], *incoming]
    slope_zero = reference.zero_flag(builder, words[7])
    chart = _flag(builder, reference, required, [slope_zero, *excluded])
    u, v = ([builder.alloc_qubits(12) for _ in range(6)] for _ in range(2))
    builder.x(u[0][0])
    _separated_direction(builder, reference, words, v[2:])
    _transfer_band(builder, reference, words, u, v, 6)
    a, b = u[0], v[0]
    n0, wronskian = words[-2:]
    b_zero = reference.zero_flag(builder, b)
    area, pivot, spare = (builder.alloc_qubits(12) for _ in range(3))
    multiply = reference.ar.mul_xor0
    emit_product = reference.ar.phase_product if phase else multiply
    rows = [[builder.alloc_qubits(12) for _ in range(5)] for _ in range(4)]

    def xor_system():
        multiply(builder, b, n0, rows[0][-1])
        with _masked_word(builder, n0, b_zero) as masked:
            multiply(builder, area, masked, rows[1][-1])
        builder.cx(denominator, rows[2][-1])
        builder.cx(wronskian, rows[3][-1])
        for j in range(4):
            multiply(builder, b, u[4 - j], rows[0][j])
            multiply(builder, a, v[4 - j], rows[0][j])
            multiply(builder, b, u[5 - j], spare)
            multiply(builder, a, v[5 - j], spare)
            multiply(builder, pivot, spare, rows[1][j])
            multiply(builder, b, u[5 - j], spare)
            multiply(builder, a, v[5 - j], spare)
            multiply(builder, area, v[4 - j], rows[1][j])
            builder.cx(u[4 - j], v[4 - j])
            with _masked_word(builder, v[4 - j], b_zero) as masked:
                multiply(builder, area, masked, rows[1][j])
            builder.cx(u[4 - j], v[4 - j])
            builder.cx(v[3 - j], rows[2][j])
            multiply(builder, denominator, u[3 - j], rows[3][j])
            if j < 3:
                multiply(builder, n0, v[2 - j], rows[3][j])

    def use_solution(solution, singular):
        active = _flag(builder, reference, [chart], singular)
        builder.cx(active, eligible)
        views = [(u, i) for i in range(3, -1, -1)] + [(v, i) for i in range(2, -1, -1)]
        for offset, weight in enumerate(solution):
            with _masked_word(builder, weight, active) as source:
                for (bank, index), target in zip(views, targets, strict=True):
                    if index >= offset:
                        emit_product(builder, source, bank[index - offset], target)
        _flag(builder, reference, [chart], singular, active)

    multiply(builder, a, v[1], area)
    multiply(builder, b, u[1], area)
    builder.cx(b, pivot)
    builder.ccx(b_zero, a, pivot)
    xor_system()
    _with_solution(builder, reference, rows, use_solution)
    xor_system()
    builder.ccx(b_zero, a, pivot)
    builder.cx(b, pivot)
    multiply(builder, b, u[1], area)
    multiply(builder, a, v[1], area)
    reference.clear_flag(builder, b, b_zero)
    for row in rows:
        for word in row:
            builder.free(word)
    for word in (area, pivot, spare):
        builder.free(word)
    _transfer_band(builder, reference, words, u, v, 6, reverse=True)
    _separated_direction(builder, reference, words, v[2:], reverse=True)
    builder.x(u[0][0])
    for word in u + v:
        builder.free(word)
    _flag(builder, reference, required, [slope_zero, *excluded], chart)
    reference.clear_flag(builder, words[7], slope_zero)
