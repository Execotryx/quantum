"""Assemble the circular routed BM locator, scaled scan, and reverse rounds."""

from typing import Any

from .bm_full_round import full_round
from .direct_forney import inplace_evaluator_and_scan
from .history_stack import HistoryStack


def routed_decoder(builder: Any, field: Any, syndromes: list[Any], masks: list[Any], *, depth: int) -> None:
    n = len(syndromes)
    if not 2 <= n <= 70 or not n < len(masks) <= 4095:
        raise ValueError("expected syndrome count in [2,70] and n < m <= 4095")
    if any(len(word) != 12 for word in (*syndromes, *masks)):
        raise ValueError("routed decoder requires 12-bit words")
    width = n // 2 + 1
    locator = [builder.alloc_qubits(12) for _ in range(width)]
    template = [builder.alloc_qubits(12) for _ in range(width)]
    counter = builder.alloc_qubits(8)
    branches = builder.alloc_qubits(n)
    history = HistoryStack(builder, depth)
    builder.x(locator[0][0])
    builder.x(template[0][0])
    for r, branch in enumerate(branches, 1):
        full_round(builder, locator, template, syndromes, r, counter, branch, history.transfer)
        history.push(builder, r)
    inplace_evaluator_and_scan(builder, field, locator, syndromes, masks)
    for r in range(n, 0, -1):
        history.pop(builder, r)
        full_round(builder, locator, template, syndromes, r, counter, branches[r - 1], history.transfer, adjoint=True)
    builder.x(template[0][0])
    builder.x(locator[0][0])
    # Keep final ancillary state visible to the verifier, including overflow.
