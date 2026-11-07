"""Fixed-word DFTHC refitting helpers, with official tensor math injected by the caller."""

from dataclasses import replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .representation import canonical_signs, validate_tree


def encode_vectors(vectors: NDArray[np.float64], edges: NDArray[np.int64], brot: int) -> NDArray[np.int64]:
    """Recover parent-before-child rotations by sweeping the tree backwards."""
    work = canonical_signs(vectors)
    validate_tree(edges, work.shape[1], 0)
    if not 1 <= brot <= 52:
        raise ValueError("angle precision outside supported quantization range")
    words = np.empty((len(work), len(edges)), dtype=np.int64)
    scale = (1 << (brot - 1)) / np.pi
    for k in reversed(range(len(edges))):
        parent, child = edges[k]
        a, b = work[:, parent].copy(), work[:, child]
        words[:, k] = np.rint(np.arctan2(b, a) * scale).astype(np.int64) % (1 << brot)
        work[:, parent] = np.hypot(a, b)
        work[:, child] = 0
    return words


class FixedWordRefit:
    """Vary lowercase weights and identity coefficients independently."""

    def __init__(self, api: Any, math: Any, inputs: Any, words: Any, brot: int) -> None:
        self.api, self.math, self.inputs = api, math, inputs
        self.brot = brot
        self.edges = api.load_tree_edges(inputs.params["tree_edges"], None)
        n = inputs.num_orbitals
        validate_tree(self.edges, n, 0)
        words = np.asarray(words)
        if (
            not 1 <= brot <= 52 or words.shape != (inputs.num_vectors, n - 1)
            or words.dtype.kind not in "iu" or np.any(words < 0) or np.any(words >= (1 << brot))
        ):
            raise ValueError("invalid fixed angle words")
        self.two_body_words = words[n:].copy()
        two_body = math.reconstruct_u_vectors(
            self.two_body_words.astype(np.float64) / (1 << (brot - 1)), self.edges
        )
        two_body /= np.linalg.norm(two_body, axis=1, keepdims=True)
        self.two_body = two_body.reshape(inputs.w.shape[:2] + (n,))
        ref = inputs.ref
        self.h1 = ref["oei"] - 0.5 * np.einsum("prrq->pq", ref["tei"])

    def evaluate(self, weight_scale: float, offset_scale: float) -> tuple[Any, Any, dict[str, Any]]:
        inputs = self.inputs
        w = weight_scale * inputs.w
        offsets = offset_scale * inputs.W
        params = {**inputs.params, "W": w, "H2_I": offsets + w.sum(axis=1)}
        # Recompute the actual offsets after floating-point NPZ serialization arithmetic.
        w, offsets, _, _ = self.api.native_inputs(params)
        x = self.math.reconstruct_x(self.two_body, w)
        x = np.tril(x) + np.swapaxes(np.tril(x, k=-1), -1, -2)
        h1_prime = self.math.build_h1_prime(
            self.h1, inputs.S, inputs.beta_1, inputs.ref["electrons"], offsets, x
        )
        _, eigenvectors = np.linalg.eigh(h1_prime)
        one_body = encode_vectors(eigenvectors.T, self.edges, self.brot)
        words = np.concatenate((one_body, self.two_body_words))
        adjusted = replace(inputs, params=params, w=w, W=offsets)
        metrics = self.api.evaluate_words(adjusted, words, brot=self.brot, tree_edges=self.edges)
        return params, words, metrics
