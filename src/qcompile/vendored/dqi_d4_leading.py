"""Leading-coordinate transfers for the admitted D4 chart factors."""


def aligned_quadratic(builder, reference, bank, kappa, *, reverse=False):
    """Multiply a reversed coefficient bank by the reversed monic quadratic."""
    positions = range(1, len(bank)) if reverse else range(len(bank) - 1, 0, -1)
    for i in positions:
        builder.cx(bank[i - 1], bank[i])
        if i >= 2:
            reference.cx(builder, bank[i - 2], bank[i], kappa)


def aligned_shear(builder, reference, source, target, variables, constants):
    """XOR a head product into an equal-width reversed coefficient bank."""
    for shift, word in variables:
        for depth in range(shift, len(target)):
            reference.ar.mul_xor0(builder, word, source[depth - shift], target[depth])
    for shift, coefficient in constants:
        for depth in range(shift, len(target)):
            reference.cx(builder, source[depth - shift], target[depth], coefficient)


def aligned_head_product(builder, reference, head, source, target):
    """XOR the low product coefficients in reversed coordinates by interpolation."""
    old = reference.folds.old
    nodes, interpolation = old.base.vandermonde(len(source) + len(head) - 1)
    for node, y in enumerate(nodes):
        output = [row[node] for row in interpolation[:len(target)]]
        old.rank_affine(builder, head, y[:len(head)], source, y[:len(source)], target, output)


def xor_leading_factor(builder, reference, heads, inputs, outputs, kappa, collapse, incoming=None):
    """XOR selected coefficients of one row times a live doubled-node factor.

    Banks map absolute powers to disjoint GF(4096) words. Any required
    missing input coefficient must be zero. A chart-dependent swap needs
    the same input powers in both banks. Each intermediate coefficient is
    computed and erased before visiting the next one.
    """
    a, b = inputs
    u, v = outputs
    h0, h1 = heads
    if incoming is not None and a.keys() != b.keys():
        raise ValueError("Incoming chart swap requires matching input powers")
    quadratic = (kappa, 1, 1)
    intermediate = sorted(
        {power - shift for power in u for shift in range(2) if power >= shift}
        | {power - shift for power in v for shift in range(3) if power >= shift}
    )

    def swap():
        if incoming is not None:
            for power in a:
                builder.cswap(incoming, a[power], b[power])

    def xor_q_word(power, target):
        for shift, coefficient in enumerate(quadratic):
            if power - shift in a:
                reference.cx(builder, a[power - shift], target, coefficient)

    swap()
    for power, target in u.items():
        xor_q_word(power, target)
    builder.cx(collapse, h1[0][0])
    for power in intermediate:
        value = builder.alloc_qubits(12)
        q_value = builder.alloc_qubits(12)
        xor_q_word(power, q_value)
        builder.ccx(collapse, q_value, value)
        if power in b:
            builder.cx(b[power], value)
        terms = [(word, a[power - shift]) for shift, word in enumerate(h0) if power - shift in a]
        for head, source in terms:
            reference.ar.mul_xor0(builder, head, source, value)
        for shift, head in enumerate(h1):
            if power + shift in u:
                reference.ar.mul_xor0(builder, head, value, u[power + shift])
        for shift, coefficient in enumerate(quadratic):
            if power + shift in v:
                reference.cx(builder, value, v[power + shift], coefficient)
        mask = builder.alloc_bits(12)
        builder.hmr(value, mask)
        builder.free(value)
        if power in b:
            builder.cz(b[power], mask)
        for head, source in terms:
            reference.ar.phase_product(builder, head, source, mask)
        builder.ccz(collapse, q_value, mask)
        builder.free(mask)
        xor_q_word(power, q_value)
        builder.free(q_value)
    builder.cx(collapse, h1[0][0])
    swap()
