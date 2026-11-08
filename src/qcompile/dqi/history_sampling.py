"""Batch the exact classical routed recurrence for history-depth sampling."""

from typing import Any

import numpy as np

from .field import GF4096


def history_statistics(syndromes: np.ndarray, field: GF4096, *, block_size: int = 4096) -> dict[str, Any]:
    """Report the same depth gates as row-by-row routed BM on the same draws."""
    if syndromes.ndim != 2 or not len(syndromes) or not 1 <= syndromes.shape[1] <= 70 or block_size < 1:
        raise ValueError("invalid DQI history sample shape")
    if syndromes.dtype.kind not in "iu" or np.any(syndromes < 0) or np.any(syndromes >= 4096):
        raise ValueError("invalid DQI history sample symbols")
    rounds = syndromes.shape[1]
    exponents = np.asarray(field.exp, dtype=np.uint16)
    logarithms = np.asarray(field.log, dtype=np.int16)
    positions = np.arange(rounds + 1, dtype=np.int16)
    histogram = np.zeros(rounds + 1, dtype=np.int64)
    maximum = np.zeros(rounds, dtype=np.int16)
    max_shifted = 0

    def multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        powers = (logarithms[a] + logarithms[b]) % 4095
        return np.where((a == 0) | (b == 0), np.uint16(0), exponents[powers])

    for start in range(0, len(syndromes), block_size):
        shots = syndromes[start:start + block_size].astype(np.uint16, copy=False)
        sigma = np.zeros((len(shots), rounds + 1), dtype=np.uint16)
        tau = np.zeros_like(sigma)
        sigma[:, 0] = tau[:, 0] = 1
        counter = np.zeros(len(shots), dtype=np.int16)
        sigma_degree = np.zeros_like(counter)
        tau_degree = np.zeros_like(counter)
        retains = np.zeros_like(counter)
        first_violation = None
        for j in range(rounds):
            delta = np.bitwise_xor.reduce(multiply(sigma[:, :j + 1], shots[:, j::-1]), axis=1)
            active = delta != 0
            replace = active & (counter >= 0)
            retain = active & ~replace
            alpha = multiply(delta, sigma[:, 0])
            width = j + 2
            tau[:, 1:width] = tau[:, :width - 1]
            tau[:, 0] = 0
            tau_degree += 1
            if np.any(active):
                max_shifted = max(max_shifted, int(tau_degree[active].max()))
            old_sigma = sigma[replace, :width]
            inverse = exponents[-logarithms[alpha[replace]] % 4095]
            sigma[replace, :width] = tau[replace, :width] ^ multiply(old_sigma, inverse[:, None])
            tau[replace, :width] = old_sigma
            sigma[retain, :width] ^= multiply(tau[retain, :width], alpha[retain, None])
            shifted_exceeded = active & (tau_degree > 35)
            previous_degree = sigma_degree[replace]
            sigma_degree[active] = np.max(
                np.where(sigma[active, :width] != 0, positions[:width], 0), axis=1,
            )
            counter = np.where(replace, -counter, counter + 1)
            retains += retain
            maximum[j] = max(maximum[j], sigma_degree.max())
            bad = np.flatnonzero(shifted_exceeded | (sigma_degree > min(j + 1, 35)))
            if len(bad):
                i = int(bad[0])
                if first_violation is None or i < first_violation["shot"] - start:
                    first_violation = {"status": "degree_violation", "shot": start + i, "round": j + 1,
                                       "degree": int(sigma_degree[i]),
                                       "shifted_degree": int(tau_degree[i]) if active[i] else 0}
            tau_degree[replace] = previous_degree
        if first_violation is not None:
            return first_violation
        histogram += np.bincount(retains, minlength=rounds + 1)
    return {"status": "complete", "shots": len(syndromes), "histogram": histogram.tolist(),
            "max_degree_by_round": maximum.tolist(), "max_active_shifted_degree": max_shifted}
