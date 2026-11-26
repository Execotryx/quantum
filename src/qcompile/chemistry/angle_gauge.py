"""Choose cosine signs in an ordered Givens tree without changing its projectors."""

import numpy as np
import numpy.typing as npt

from .representation import validate_tree


def recode_cosine_signs(
    words: npt.ArrayLike,
    edges: npt.ArrayLike,
    brot: int,
    cosine_negative: npt.ArrayLike,
    *,
    root: int = 0,
) -> npt.NDArray[np.int64]:
    """Assign quadrant markers while preserving every represented vector up to sign.

    The child starts with zero amplitude at every edge. The sign constraints
    propagate backward from the final vector. A zero cosine erases the parent
    amplitude, so its input sign is determined by the outgoing child alone.
    The input sign at the root becomes a single overall sign for the vector.
    """
    table, requested = np.asarray(words), np.asarray(cosine_negative)
    if type(brot) is not int or not 2 <= brot <= 52:
        raise ValueError("The angle gauge requires between 2 and 52 bits")
    if (table.ndim != 2 or not all(table.shape) or table.dtype.kind not in "iu"
            or requested.shape != table.shape or requested.dtype.kind != "b"):
        raise ValueError("Expected integer word rows and a matching Boolean marker table")
    turn = 1 << brot
    if np.any((table < 0) | (table >= turn)):
        raise ValueError("Angle words are outside the specified precision")
    tree = validate_tree(edges, table.shape[1] + 1, root)
    half, quarter = turn // 2, turn // 4
    old_sine = (table & half) != 0
    old_cosine = ((table & quarter) != 0) ^ old_sine
    remainder = table.astype(np.int64, copy=False) % half
    alpha = np.minimum(remainder, half - remainder)

    required = np.zeros((len(table), len(tree) + 1), dtype=bool)
    result = np.empty(table.shape, dtype=np.int64)
    for column in range(len(tree) - 1, -1, -1):
        parent, child = tree[column]
        cosine = requested[:, column]
        magnitude = alpha[:, column]
        zero_cosine = magnitude == quarter
        previous = required[:, parent] ^ old_cosine[:, column] ^ cosine
        sine_at_quarter = ~cosine
        previous[zero_cosine] = (
            old_sine[zero_cosine, column] ^ required[zero_cosine, child] ^ sine_at_quarter[zero_cosine]
        )
        sine = old_sine[:, column] ^ previous ^ required[:, child]
        offset = np.where(cosine ^ sine, half - magnitude, magnitude)
        result[:, column] = (offset + np.where(sine, half, 0)) % turn
        required[:, parent] = previous
    return result
