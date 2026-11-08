"""Fixed-decoded-basis weight fitting and exact precision-ladder gates."""

import time
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .factorization import direct_residual, factor_rows, gram_residual, svec

Floats = NDArray[np.float64]


def passes_margins(metrics: dict[str, Any]) -> bool:
    """Apply all decoded project margins; malformed/nonfinite metrics fail."""
    try:
        values = [float(metrics[k]) for k in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff")]
        e1, e2, lam, gap, _ = values
        return bool(all(np.isfinite(values)) and e1 <= 0.0195 and e2 <= 0.0195
                    and e1 >= 0 and e2 >= 0 and lam >= 49.05 and gap >= 3.916
                    and 0 < gap <= 2 * lam and metrics["gap_in_domain"] is True)
    except (KeyError, TypeError, ValueError):
        return False


def precision_ladder(evaluate_step: Callable[[int], dict[str, Any]]) -> dict[str, Any]:
    """Descend the registered ladder, stopping at the first exact gate failure."""
    steps = []
    last_passing = None
    for bits in (12, 11, 10, 9, 8):
        result = evaluate_step(bits)
        eligible = passes_margins(result["metrics"]) and result.get("eligible", True) is True
        steps.append({"brot": bits, "eligible": eligible, "result": result})
        if not eligible:
            if not result.get("converged"):
                status = "budget_limited" if result.get("capped") else "inconclusive"
            else:
                status = "step_failed"
            return {"status": status, "last_passing": last_passing, "steps": steps}
        last_passing = bits
    return {"status": "ladder_passed", "last_passing": last_passing, "steps": steps}


def refit_weights(target: Floats, decoded: Floats, initial: Floats, *,
                  max_evaluations: int, deadline: float) -> dict[str, Any]:
    """Fit every weight with decoded vectors fixed; retain the best evaluated point."""
    if type(max_evaluations) is not int or not 1 <= max_evaluations <= 5000:
        raise ValueError("invalid registered precision refit cap")
    lengths = np.linalg.norm(decoded, axis=-1, keepdims=True)
    if not np.all(np.isfinite(lengths)) or np.any(lengths == 0):
        raise ValueError("invalid decoded basis")
    unit = decoded / lengths
    features = svec(unit[..., :, None] * unit[..., None, :])
    r, b, c = initial.shape
    if unit.shape[:2] != (r, b):
        raise ValueError("decoded basis and weights disagree")
    norm = float(np.vdot(target, target))
    best = initial.copy()
    best_value = float("inf")
    history: list[float] = []
    converged = False

    class Stop(Exception):
        pass

    def objective(flat):
        nonlocal best, best_value
        if len(history) >= max_evaluations or time.monotonic() >= deadline:
            raise Stop
        weights = flat.reshape(r, b, c)
        squared, gradient = gram_residual(target, factor_rows(features, weights), norm)
        if not np.isfinite(squared) or squared < 0:
            raise ValueError("invalid Gram residual during precision refit")
        if squared < best_value:
            best_value, best = squared, weights.copy()
        history.append(float(np.sqrt(best_value)))
        grad_w = np.einsum("rcd,rbd->rbc", gradient.reshape(r, c, -1), features, optimize=True)
        return squared, grad_w.ravel()

    try:
        result = minimize(objective, initial.ravel(), jac=True, method="L-BFGS-B",
                          options={"maxiter": max_evaluations, "maxfun": max_evaluations})
        converged = bool(result.success)
        reason = str(result.message)
    except Stop:
        reason = "registered evaluation or wall cap"
    capped = len(history) >= max_evaluations or time.monotonic() >= deadline
    return {"weights": best, "residual": direct_residual(target, factor_rows(features, best)),
            "evaluations": len(history), "running_best": history, "converged": converged,
            "capped": capped, "reason": reason}
