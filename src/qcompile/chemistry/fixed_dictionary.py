"""Weight fitting with a frozen, decoded DFTHC projector dictionary."""

import numpy as np
from numpy.typing import NDArray

Floats = NDArray[np.float64]


def truncate_channels(features: Floats, weights: Floats, offsets: Floats, copies: int) -> tuple[Floats, Floats]:
    """Project weights and native offsets onto the leading physical channels."""
    if not 1 <= copies <= weights.shape[2] or offsets.shape != (weights.shape[0], weights.shape[2]):
        raise ValueError("invalid channel dimensions")
    if copies == weights.shape[2]:
        return weights.copy(), offsets.copy()
    physical = features.swapaxes(1, 2) @ weights
    eig, vectors = np.linalg.eigh(physical.swapaxes(1, 2) @ physical)
    retained = vectors[:, :, -copies:].copy()
    pivots = np.argmax(np.abs(retained), axis=1, keepdims=True)
    retained *= np.where(np.take_along_axis(retained, pivots, axis=1) < 0, -1, 1)
    return weights @ retained, (offsets[:, None, :] @ retained)[:, 0]


class FixedDictionaryGram:
    """Evaluate the residual and weight gradient in the smaller dictionary coordinates."""

    def __init__(self, target: Floats, features: Floats) -> None:
        groups, bases, width = features.shape
        if target.shape != (width, width):
            raise ValueError("dictionary and target dimensions disagree")
        flat = features.reshape(groups * bases, width)
        blocks = (flat @ flat.T).reshape(groups, bases, groups, bases)
        self.gram = np.ascontiguousarray(blocks.transpose(2, 0, 1, 3).reshape(groups, groups * bases, bases))
        self.projected = features @ target @ features.swapaxes(1, 2)
        self.norm_sq = float(np.vdot(target, target))

    def objective(self, weights: Floats) -> tuple[float, Floats]:
        groups, bases, copies = weights.shape
        weighted = (self.gram @ weights).reshape(groups, groups, bases, copies)
        weighted = weighted.transpose(1, 2, 0, 3).reshape(groups, bases, groups * copies)
        blocks = weights.swapaxes(1, 2) @ weighted
        projected = self.projected @ weights
        squared = self.norm_sq - 2 * np.vdot(weights, projected) + np.vdot(blocks, blocks)
        gradient = 4 * (weighted @ blocks.reshape(groups * copies, groups, copies).transpose(1, 0, 2) - projected)
        return float(squared), gradient
