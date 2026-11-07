"""High-precision discrete relative minimax fits for the existing Horner layout."""

from decimal import Decimal, localcontext

from .direct import DirectFormat


def _fit(mesh: list[Decimal], roots: list[Decimal], degree: int) -> list[Decimal]:
    """Exchange alternating extrema on a fixed mesh, with a bounded iteration count."""
    size = degree + 2
    points = [i * (len(mesh) - 1) // (size - 1) for i in range(size)]
    basis = [[root * x**power if power else root for power in range(degree + 1)]
             for x, root in zip(mesh, roots, strict=True)]
    for _ in range(40):
        rows = [basis[j] + [Decimal((-1)**i), Decimal(1)] for i, j in enumerate(points)]
        for i in range(size):
            pivot = max(range(i, size), key=lambda j: abs(rows[j][i]))
            rows[i], rows[pivot] = rows[pivot], rows[i]
            scale = rows[i][i]
            rows[i] = [entry / scale for entry in rows[i]]
            for j, row in enumerate(rows):
                if j != i:
                    rows[j] = [a - row[i] * b for a, b in zip(row, rows[i], strict=True)]
        coefficients = [row[-1] for row in rows[:-1]]
        errors = [
            sum((c * v for c, v in zip(coefficients, row, strict=True)), Decimal(-1))
            for row in basis
        ]
        extrema = [0] + [
            i for i in range(1, len(errors) - 1)
            if (errors[i] >= max(errors[i - 1], errors[i + 1])
                or errors[i] <= min(errors[i - 1], errors[i + 1]))
        ] + [len(errors) - 1]
        exchanged: list[int] = []
        for i in extrema:
            if exchanged and errors[i].is_signed() == errors[exchanged[-1]].is_signed():
                if abs(errors[i]) > abs(errors[exchanged[-1]]):
                    exchanged[-1] = i
            else:
                exchanged.append(i)
        if len(exchanged) != size:
            raise ValueError("relative minimax fit lost alternation")
        if exchanged == points:
            return coefficients
        points = exchanged
    raise ValueError("relative minimax fit did not converge within the exchange budget")


def coefficient_table(fmt: DirectFormat) -> tuple[tuple[int, ...], ...]:
    """Quantize alternating coefficients for dyadic segments and left-edge Horner."""
    degree = len(fmt.fractional) - 1
    if degree not in (2, 3):
        raise ValueError("minimax fits support degree two and three")
    segments = 1 << fmt.segment_bits
    with localcontext(prec=64):
        mesh = [Decimal(i) / 128 for i in range(129)]
        rows = []
        for address in range(segments, 4 * segments):
            roots = [((address + x) / segments).sqrt() for x in mesh]
            coefficients = _fit(mesh, roots, degree)
            row = []
            for i, (value, frac, width) in enumerate(zip(coefficients, fmt.fractional, fmt.widths, strict=True)):
                magnitude = value * (-segments)**i
                word = round(magnitude * (1 << frac))
                if magnitude < 0 or not 0 <= word < 1 << width:
                    raise ValueError("minimax coefficient does not fit alternating Horner layout")
                row.append(word)
            rows.append(tuple(row))
        return tuple(rows)
