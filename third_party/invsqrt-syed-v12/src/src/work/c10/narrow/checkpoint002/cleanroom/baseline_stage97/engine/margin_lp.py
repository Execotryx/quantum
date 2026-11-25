# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Deterministic NumPy-only barrier LP for frozen-angle fitting.

Maximize the smallest remaining phase tolerance subject to all active input
constraints and bounded angle nudges. All units are 1e-12 turns.
"""
from __future__ import annotations

import numpy as np

from canonical_numeric import (dot, gram, logarithm, matvec, ordered_sum,
                               solve, transpose_matvec)


def barrier_lp(features, error, tolerance, *, angle_bound=5.0,
               initial=None, accuracy=1e-6):
    """Maximize margin with |error+F*w|+margin<=tolerance.

    Units are 1e-12 turns. Angle boxes make the numerical problem bounded
    even when this exchange subset does not span all 45 phase features.
    """
    dimension = features.shape[1]
    n = len(features)
    plus = np.column_stack((features, np.ones(n)))
    minus = np.column_stack((-features, np.ones(n)))
    box = np.column_stack((np.eye(dimension), np.zeros(dimension)))
    matrix = np.vstack((plus, minus, box, -box))
    bound = np.concatenate((tolerance-error, tolerance+error,
                            np.full(2*dimension, angle_bound)))
    if initial is None:
        point = np.zeros(dimension+1)
    else:
        point = np.asarray(initial, dtype=float).copy()
        point[:-1] = np.clip(point[:-1], -angle_bound*0.99, angle_bound*0.99)
    point[-1] = min(float((bound[:2*n]-matvec(matrix[:2*n, :-1], point[:-1])).min())-1, point[-1])
    objective = np.zeros(dimension+1)
    objective[-1] = -1
    schedule = [1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 3e-6, 1e-6, 3e-7, 1e-7]
    total_steps = 0
    for mu in schedule:
        for _ in range(70):
            slack = bound-matvec(matrix, point)
            if np.any(slack <= 0):
                raise ArithmeticError('Barrier iterate left the feasible set.')
            inverse = 1/slack
            gradient = objective+mu*transpose_matvec(matrix, inverse)
            scaled = matrix*inverse[:, None]
            hessian = mu*gram(scaled)
            # A minute regularizer controls nearly invisible angle directions.
            hessian += np.eye(dimension+1)*max(1e-14, float(ordered_sum(hessian.diagonal()))*1e-16/(dimension+1))
            direction = solve(hessian, -gradient)
            decrease = dot(gradient, direction)
            if -decrease/2 < min(accuracy*0.01, mu*0.01):
                break
            change = matvec(matrix, direction)
            relevant = change > 0
            step = min(1.0, 0.99*float((slack[relevant]/change[relevant]).min())) if relevant.any() else 1.0
            old_merit = dot(objective, point)-mu*float(ordered_sum(logarithm(slack)))
            accepted = False
            for _ in range(40):
                trial = point+step*direction
                trial_slack = bound-matvec(matrix, trial)
                if np.all(trial_slack > 0):
                    merit = dot(objective, trial)-mu*float(ordered_sum(logarithm(trial_slack)))
                    if merit <= old_merit+0.01*step*decrease:
                        point = trial
                        accepted = True
                        break
                step *= 0.5
            if not accepted:
                break
            total_steps += 1
    return point, dict(newton_steps=total_steps, subset_constraints=2*n)
