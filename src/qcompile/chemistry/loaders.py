"""Shape-generic banked ANGLE loaders and pinned complete-cost ranking."""

from typing import Any

import numpy as np

from .representation import batch_words


def max_batch(rows: int, brot: int, low_bits: int, *, cap: int = 128) -> int:
    """Maximum word-register count allowed by the banked circuit width."""
    if type(rows) is not int or rows < 3 or type(brot) is not int or not 1 <= brot <= 52:
        raise ValueError("invalid row count or precision")
    address_bits = (rows - 1).bit_length()
    if type(low_bits) is not int or not 1 <= low_bits < address_bits:
        raise ValueError("invalid bank split")
    high_bits = address_bits - low_bits
    scratch = max(low_bits + int(high_bits > 1), high_bits - 1)
    return max(0, (cap - address_bits - scratch) // brot)


def banked_circuit(km: Any, api: Any, delta: Any, brot: int, *, low_bits: int) -> Any:
    """Build a reversible XOR lookup with clean bank and unary-tree workspace."""
    table = np.asarray(delta)
    if table.ndim != 2 or table.shape[0] < 3 or table.dtype.kind not in "iu":
        raise ValueError("expected an integer table with at least three rows")
    rows, width = table.shape
    address_bits = (rows - 1).bit_length()
    if (type(brot) is not int or not 1 <= brot <= 52 or width < 1
            or type(low_bits) is not int or not 1 <= low_bits < address_bits
            or np.any(table < 0) or np.any(table >= (1 << brot))):
        raise ValueError("invalid banked lookup dimensions or values")
    high_bits = address_bits - low_bits
    flag_slots = int(high_bits > 1)
    scratch_size = max(low_bits + flag_slots, high_bits - 1)
    if width > max_batch(rows, brot, low_bits):
        raise ValueError("banked lookup exceeds the 128-qubit cap")
    builder = km.CircuitBuilder()
    selection = builder.create_quantum_register(address_bits, api.SELECTION_REGISTER)
    words = [builder.create_quantum_register(brot, api.word_register(j)) for j in range(width)]
    scratch = list(builder.alloc_qubits(scratch_size))
    flag, helpers = scratch[0], scratch[1:high_bits - 1]
    bits = list(reversed(list(selection)))
    high, low = bits[:-low_bits], bits[-low_bits:]

    def tree(control: Any, level: int, start: int, end: int) -> None:
        if start >= rows:
            return
        if end - start == 1:
            for register, word in zip(words, table[start], strict=True):
                value = int(word)
                while value:
                    bit = value & -value
                    builder.cx(control, register[bit.bit_length() - 1])
                    value ^= bit
            return
        middle = (start + end) // 2
        address, child = low[level], scratch[level + flag_slots]
        builder.x(address)
        builder.init_and(control, address, child)
        builder.x(address)
        tree(child, level + 1, start, middle)
        builder.cx(control, child)
        tree(child, level + 1, middle, end)
        builder.del_and(control, address, child)

    chain = list(zip([high[0], *helpers], high[1:], [*helpers, flag], strict=True)) if high_bits > 1 else []
    size = 1 << low_bits
    for bank, start in enumerate(range(0, rows, size)):
        negated = [bit for k, bit in enumerate(reversed(high)) if not bank & (1 << k)]
        for bit in negated:
            builder.x(bit)
        for pair in chain:
            builder.init_and(*pair)
        for pair in reversed(chain[:-1]):
            builder.del_and(*pair)
        tree(flag if chain else high[0], 0, start, start + size)
        for pair in chain[:-1]:
            builder.init_and(*pair)
        for pair in reversed(chain):
            builder.del_and(*pair)
        for bit in negated:
            builder.x(bit)
    return builder.finish_circuit()


def family(km: Any, api: Any, words: Any, brot: int, batch: int, low_bits: int) -> list[Any]:
    """Construct contiguous XOR-delta circuits for an in-memory word table."""
    _, deltas = batch_words(words, batch, brot)
    return [banked_circuit(km, api, delta, brot, low_bits=low_bits) for delta in deltas]


def verify_nonzero_xor(km: Any, api: Any, circuits: list[Any], words: Any,
                       brot: int, batch: int, seed: int) -> dict[str, int]:
    """Check arbitrary targets, selection, workspace and phase on the full binary domain."""
    table = np.asarray(words)
    _, deltas = batch_words(table, batch, brot)
    if len(circuits) != len(deltas):
        raise ValueError("family size does not match angle batches")
    layout = api.register_layout(circuits)
    address_count = 1 << len(layout.selection)
    if (address_count < len(table) or layout.brot != brot or layout.batch_size != batch
            or len(layout.selection) != (len(table) - 1).bit_length()):
        raise ValueError("family register layout disagrees with the table")
    addresses = np.arange(address_count, dtype=np.int64)
    selection = ((addresses[None, :] >> np.arange(len(layout.selection))[:, None]) & 1).astype(bool)
    bits = np.arange(brot, dtype=np.int64)
    initial = np.random.default_rng(seed).integers(0, 1 << brot, size=(address_count, batch), dtype=np.int64)
    sim = km.Simulator(batch_size=address_count, seed=seed)
    sim.use_same_registers_as(circuits[0])
    sim.write_across_shots(layout.selection, selection)
    for index, register in enumerate(layout.words):
        sim.write_across_shots(register, ((initial[:, index][None, :] >> bits[:, None]) & 1).astype(bool))
    expected = initial.copy()
    padded = [np.pad(delta, ((0, address_count - len(table)), (0, 0))) for delta in deltas]
    for index in [*range(len(circuits)), *reversed(range(len(circuits)))]:
        sim.do(circuits[index])
        api._check_state(sim, circuits[index], layout, selection, f"nonzero ANGLE_{index}")
        expected ^= padded[index]
        actual = np.stack([(1 << bits) @ sim.read_across_shots(register) for register in layout.words], axis=1)
        if not np.array_equal(actual, expected):
            raise ValueError(f"nonzero XOR fixture mismatch at ANGLE_{index}")
    if not np.array_equal(expected, initial):
        raise ValueError("nonzero XOR fixture did not restore the initial targets")
    return {"valid_addresses": len(table), "padding_addresses": address_count - len(table),
            "shots": address_count, "circuit_applications": 2 * len(circuits)}


def rank_complete_cost(api: Any, inputs: Any, candidates: list[tuple[int, list[Any], float]],
                       brot: int, lambda_eff: float) -> list[dict[str, Any]]:
    """Rank native-verified families with the pinned resource-cost function.

    Each Toffoli value must cover both forward and reverse passes, as returned
    by the pinned circuit verifier. This ranking is not an accuracy decision.
    """
    if not np.isfinite(lambda_eff) or lambda_eff <= 0 or not candidates:
        raise ValueError("expected positive lambda_eff and at least one candidate")
    results = []
    for batch, circuits, toffoli in candidates:
        if not np.isfinite(toffoli) or toffoli < 0:
            raise ValueError("invalid verified Toffoli count")
        layout = api.register_layout(circuits)
        r, b, _ = inputs.w.shape
        if (layout.batch_size != batch or layout.brot != brot
                or len(layout.selection) != (inputs.num_orbitals + r * b - 1).bit_length()
                or len(circuits) != (inputs.num_orbitals - 2 + batch) // batch):
            raise ValueError("candidate layout does not match its declared shape")
        resources = api.resource_costs(inputs, circuits, brot, toffoli)
        if not resources["angles_within_cap"]:
            raise ValueError("ANGLE family exceeds the qubit cap")
        results.append({"batch": batch, "resources": resources,
                        "modeled_cost": float(lambda_eff * resources["toffoli"] * resources["qubits"])})
    return sorted(results, key=lambda row: (row["modeled_cost"], row["batch"]))
