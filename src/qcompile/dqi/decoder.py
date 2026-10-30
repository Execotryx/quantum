"""Independent locator algorithms, sharing only field operations and recovery.

BM and EEA share Vandermonde recovery: syndrome re-encoding and polynomial
reference fixtures are required to cover that common-mode dependency. Position j
means X=alpha^j and S_i=sum(e_j X^(i+1)), with ascending polynomial coefficients.
"""

from qcompile.errors import ValidationError

from .field import GF4096


def syndrome(errors: dict[int, int], field: GF4096, count=70):
    result = [0] * count
    if len(errors) > 35:
        raise ValidationError("error exceeds supported radius 35")
    for j, value in errors.items():
        if type(j) is not int or not 0 <= j < 4095 or not 0 < value < 4096:
            raise ValidationError("invalid error position or nonzero symbol")
        point = field.exp[j]
        power = point
        for i in range(count):
            result[i] ^= field.mul(value, power)
            power = field.mul(power, point)
    return result


def _syndromes(values, field):
    if len(values) != 70:
        raise ValidationError("expected exactly 70 syndrome symbols")
    return [field.symbol(x) for x in values]


def bm_locator(values, field):
    values = _syndromes(values, field)
    c, b = [1] + [0] * 70, [1] + [0] * 70
    degree, offset, previous = 0, 1, 1
    for index, value in enumerate(values):
        discrepancy = value
        for i in range(1, degree + 1):
            discrepancy ^= field.mul(c[i], values[index - i])
        if discrepancy == 0:
            offset += 1
            continue
        old = c[:]
        scale = field.div(discrepancy, previous)
        for i in range(71 - offset):
            c[i + offset] ^= field.mul(scale, b[i])
        if 2 * degree <= index:
            degree = index + 1 - degree
            b, previous, offset = old, discrepancy, 1
        else:
            offset += 1
    if degree > 35:
        raise ValidationError("BM locator outside unique decoding radius")
    return c[: degree + 1]


def _trim(p):
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def _add(a, b):
    result = [0] * max(len(a), len(b))
    for i, value in enumerate(a):
        result[i] ^= value
    for i, value in enumerate(b):
        result[i] ^= value
    return _trim(result)


def _multiply(a, b, field):
    result = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i + j] ^= field.mul(x, y)
    return _trim(result)


def _divide(a, b, field):
    remainder = _trim(a[:])
    b = _trim(b[:])
    if b == [0]:
        raise ZeroDivisionError("zero polynomial divisor")
    quotient = [0] * max(1, len(a) - len(b) + 1)
    while remainder != [0] and len(remainder) >= len(b):
        offset = len(remainder) - len(b)
        factor = field.div(remainder[-1], b[-1])
        quotient[offset] = factor
        for i, value in enumerate(b):
            remainder[offset + i] ^= field.mul(value, factor)
        _trim(remainder)
    return _trim(quotient), remainder


def eea_locator(values, field):
    values = _syndromes(values, field)
    if not any(values):
        return [1]
    previous, remainder = [0] * 70 + [1], _trim(values[:])
    v_previous, v = [0], [1]
    while len(remainder) - 1 >= 35:
        quotient, next_remainder = _divide(previous, remainder, field)
        previous, remainder = remainder, next_remainder
        v_previous, v = v, _add(v_previous, _multiply(quotient, v, field))
        if remainder == [0]:
            raise ValidationError("EEA has zero remainder outside supported domain")
    if v[0] == 0 or len(v) > 36:
        raise ValidationError("EEA locator cannot be normalized")
    return [field.div(value, v[0]) for value in v]


def recover(values, locator, field):
    degree = len(locator) - 1
    positions = [j for j in range(4095) if field.evaluate(locator, field.exp[-j % 4095]) == 0]
    if len(positions) != degree:
        raise ValidationError("locator root count does not match degree")
    # Solve S1..Sw=sum(e_j X_j^i); no Forney convention is assumed.
    matrix = []
    for i in range(degree):
        matrix.append([field.exp[(j * (i + 1)) % 4095] for j in positions] + [values[i]])
    for col in range(degree):
        pivot = next((r for r in range(col, degree) if matrix[r][col]), None)
        if pivot is None:
            raise ValidationError("singular magnitude recovery")
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = field.inv(matrix[col][col])
        matrix[col] = [field.mul(v, scale) for v in matrix[col]]
        for row in range(degree):
            if row != col and matrix[row][col]:
                factor = matrix[row][col]
                matrix[row] = [
                    a ^ field.mul(factor, b) for a, b in zip(matrix[row], matrix[col], strict=True)
                ]
    result = {j: matrix[i][-1] for i, j in enumerate(positions)}
    if any(v == 0 for v in result.values()) or syndrome(result, field) != list(values):
        raise ValidationError("recovered error does not reproduce full syndrome")
    return result


def decode(values, field, algorithm="bm"):
    if algorithm not in ("bm", "eea"):
        raise ValidationError("unknown decoder")
    locator = (bm_locator if algorithm == "bm" else eea_locator)(values, field)
    return recover(values, locator, field)


def mask_parity(errors, mask: int):
    if type(mask) is not int or not 0 <= mask < 1 << 49140:
        raise ValidationError("mask must be a 49140-bit unsigned integer")
    parity = 0
    for position, symbol in errors.items():
        if type(position) is not int or not 0 <= position < 4095 or not 0 < symbol < 4096:
            raise ValidationError("invalid error vector")
        parity ^= ((mask >> (12 * position)) & symbol).bit_count() & 1
    return parity


def failure_summary(events):
    """Overlapping labels retained; a failed trajectory contributes only once."""
    labels = ("decoder_disagreement", "wrong_phase", "register_corruption", "dirty_workspace")
    result = dict.fromkeys(labels, 0)
    failures = completed = 0
    for event in events:
        if set(event) != set(labels) or any(type(value) is not bool for value in event.values()):
            raise ValidationError("failure event needs four explicit boolean diagnostics")
        completed += 1
        failures += any(event[key] for key in labels[1:])
        for key in labels:
            result[key] += event[key]
    return {"completed": completed, "trajectory_failures": failures, "diagnostics": result}
