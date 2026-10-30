"""Report-derived objectives, explicitly estimates until official reconciliation."""

import math
from decimal import Decimal, localcontext

from scipy.stats import beta

from qcompile.errors import ValidationError
from qcompile.io import nonnegative_int, positive_int

DELTA = 2.0**-128


def finite_positive(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValidationError(f"{name} must be finite and positive")
    return value


def cp_upper(k: int, n: int, delta: float = DELTA) -> float:
    positive_int(n, "n")
    nonnegative_int(k, "k")
    if k > n or not 0 < delta < 1 or not math.isfinite(delta):
        raise ValidationError("invalid binomial confidence inputs")
    if k == n:
        return 1.0
    if k == 0:
        return -math.expm1(math.log(delta) / n)
    result = float(beta.isf(delta, k + 1, n - k))
    if not math.isfinite(result) or not k / n < result <= 1:
        raise ValidationError("beta inverse-survival solver failed")
    return result


def log_binomial_cdf_decimal(k: int, n: int, p, precision=90) -> Decimal:
    """Independent exact-combination lower-tail recurrence for CP fixture checks.

    Call above the mode (p > k/n). This avoids sharing SciPy's beta kernel.
    """
    positive_int(n, "n")
    nonnegative_int(k, "k")
    with localcontext() as ctx:
        ctx.prec = precision
        p = Decimal(str(p))
        if not 0 < p < 1 or k >= n or p <= Decimal(k) / n:
            raise ValidationError("tail fixture requires k<n and p>k/n")
        term = Decimal(math.comb(n, k)) * p**k * (1 - p) ** (n - k)
        total = term
        for j in range(k, 0, -1):
            term *= Decimal(j) * (1 - p) / (Decimal(n - j + 1) * p)
            total += term
            if term < total * Decimal(10) ** -(precision - 10):
                break
        return +total.ln()


def repetition(epsilon: float) -> float:
    if not math.isfinite(epsilon) or epsilon < 0 or epsilon >= 1 / 16:
        raise ValidationError("DQI confidence bound must be in [0,1/16)")
    # log1p keeps the distance from the rejection threshold near 1/16.
    distance = 2 * (1 / 16 - epsilon) / (0.25 + math.sqrt(epsilon))
    return math.log(2) / -math.log1p(-distance)


def dqi_cost(q: int, t: int, k: int, n: int) -> dict:
    positive_int(q, "q")
    positive_int(t, "t")
    upper = cp_upper(k, n)
    penalty = repetition(upper)
    cost = penalty * q * q * t
    finite_positive(cost, "DQI cost")
    return {"epsilon_upper": upper, "R": penalty, "cost": cost, "kind": "estimate"}


def rotation_price(margin_turns: float, n_rot: int, toffoli: int, t_gates: int) -> dict:
    finite_positive(margin_turns, "minimum wrapped margin in turns")
    for name, value in [("n_rot", n_rot), ("toffoli", toffoli), ("t_gates", t_gates)]:
        nonnegative_int(value, name)
    if n_rot:
        log_epsilon = math.log(math.pi) + math.log(margin_turns) - math.log(n_rot)
        charge = 0.56 * (-log_epsilon / math.log(2)) + 5.3
        if charge <= 0 or not math.isfinite(charge):
            raise ValidationError("invalid fine-rotation synthesis charge")
        epsilon = math.exp(log_epsilon)
        if epsilon == 0:
            raise ValidationError("allocated rotation error underflows binary64")
    else:
        charge, epsilon = 0.0, None
    total_t = t_gates + n_rot * charge
    c = toffoli + total_t / 4
    if not math.isfinite(c):
        raise ValidationError("non-finite rotation cost")
    return {
        "kind": "estimate",
        "minimum_margin_turns": margin_turns,
        "minimum_margin_phase64_units": margin_turns * 2**64,
        "n_rot": n_rot,
        "allocated_error_radians": epsilon,
        "T_per_fine_rotation": charge,
        "total_T_equivalent": total_t,
        "C": c,
        "rounding": "unrounded report formula; official aggregation unresolved",
    }


def chemistry_cost(
    *, residual1, residual2, normalization, e_sos, q_total, t_total, max_angle_width, e_upper=-22140.27335
) -> dict:
    values = (residual1, residual2, normalization, e_sos, e_upper)
    if not all(math.isfinite(v) for v in values):
        raise ValidationError("non-finite chemistry metric")
    positive_int(q_total, "Q_tot")
    positive_int(t_total, "T_tot")
    positive_int(max_angle_width, "max_angle_width")
    if not (0 <= residual1 <= 0.020 and 0 <= residual2 <= 0.020):
        raise ValidationError("coefficient residual exceeds 0.020 Ha")
    gap = e_upper - e_sos
    if not (normalization > 49 and gap > 3.914898 and 0 < gap < 2 * normalization):
        raise ValidationError("chemistry strict normalization/gap constraint failed")
    if max_angle_width > 128:
        raise ValidationError("angle circuit exceeds 128 qubits")
    effective = math.sqrt(gap * (2 * normalization - gap))
    cost = effective * q_total * t_total
    finite_positive(cost, "chemistry cost")
    return {
        "kind": "estimate",
        "gap": gap,
        "lambda_eff": effective,
        "cost": cost,
        "margins": {
            "residual1": 0.020 - residual1,
            "residual2": 0.020 - residual2,
            "normalization": normalization - 49,
            "gap_floor": gap - 3.914898,
            "gap_ceiling": 2 * normalization - gap,
            "angle_width": 128 - max_angle_width,
        },
    }


def aggregate(baselines: dict, costs: dict) -> float:
    if set(baselines) != {"invsqrt", "dqi", "dfthcsos"} or set(costs) != set(baselines):
        raise ValidationError("all three benchmark costs are required")
    logs = [
        math.log(finite_positive(baselines[k], k)) - math.log(finite_positive(costs[k], k)) for k in baselines
    ]
    result = math.exp(math.fsum(logs) / 3)
    finite_positive(result, "aggregate score")
    return result
