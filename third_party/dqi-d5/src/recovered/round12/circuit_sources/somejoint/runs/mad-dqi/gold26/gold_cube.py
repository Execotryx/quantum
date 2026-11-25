"""Zero-scratch reversible XOR of a checked GF4096 cube.

New Hermitian-norm specialization; polynomial modulus 0x1053. The circuit
uses the checked, fixed 26-AND data file, not the live heuristic output.
"""
from functools import cache
import json
from pathlib import Path


@cache
def data():
    result = json.loads(Path(__file__).with_name("hermitian12-search-check.json").read_text())
    assert result["degree"] == 12 and result["power"] == 3
    assert result["failures"] == 0 and result["truth_table_inputs"] == 4096
    return result


def xor_cube(b, source, target):
    """target ^= source**3; source and arbitrary target are disjoint words."""
    assert len(source) == len(target) == 12
    for u, v, weight in data()["terms"]:
        # First parity U in p; express V in the resulting coordinates.
        p = (u & -u).bit_length() - 1
        first = [(i, p) for i in range(12) if i != p and u >> i & 1]
        transformed_v = v ^ ((u ^ (1 << p)) if v >> p & 1 else 0)
        eligible = transformed_v & ~(1 << p)
        assert eligible
        q = (eligible & -eligible).bit_length() - 1
        second = [(i, q) for i in range(12) if i != q and transformed_v >> i & 1]
        r = (weight & -weight).bit_length() - 1
        output = [i for i in range(12) if i != r and weight >> i & 1]
        for i, j in first + second:
            b.cx(source[i], source[j])
        for i in output:
            b.cx(target[r], target[i])
        b.ccx(source[p], source[q], target[r])
        for i in reversed(output):
            b.cx(target[r], target[i])
        for i, j in reversed(first + second):
            b.cx(source[i], source[j])
    for i, column in enumerate(data()["linear_columns"]):
        for j in range(12):
            if column >> j & 1:
                b.cx(source[i], target[j])


def main():
    import argparse
    import sys
    import time
    import numpy as np
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import runtime
    from common import km
    start = time.monotonic()
    b = runtime.make_builder()
    source = b.create_quantum_register(12, name="cube_source")
    target = b.create_quantum_register(12, name="cube_target")
    xor_cube(b.native, source, target)
    circuit = b.finish_circuit()
    seed = 2026102551
    shots = 4096
    rng = np.random.default_rng(seed)
    xs = np.arange(shots, dtype=np.uint16)
    ys = rng.integers(0, 4096, size=shots, dtype=np.uint16)
    field = km.GF2Field(12)
    expected = ys ^ np.array([field.pow(int(x), 3) for x in xs], dtype=np.uint16)
    bits = np.arange(12, dtype=np.uint16)[:, None]
    sim = km.Simulator(batch_size=shots, seed=seed)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(source, ((xs[None, :] >> bits) & 1).astype(bool))
    sim.write_across_shots(target, ((ys[None, :] >> bits) & 1).astype(bool))
    sim.do(circuit)
    assert np.array_equal(sim.read_across_shots(source), ((xs[None, :] >> bits) & 1).astype(bool))
    assert np.array_equal(sim.read_across_shots(target), ((expected[None, :] >> bits) & 1).astype(bool))
    assert not sim.read_phase_flipped_across_shots().any()
    stats = circuit.operation_statistics()
    assert stats.num_toffoli_like == data()["and_count"]
    assert circuit.num_qubits == 24
    record = {"status": "PASS", "scope": "native complete input cube XOR microtest, not official DQI",
              "shots": shots, "seed": seed, "qubits": circuit.num_qubits, "scratch_qubits": 0,
              "toffoli_count": stats.num_toffoli_like, "t_count": stats.num_t_like,
              "instructions": len(circuit), "source_restoration_failures": 0,
              "target_failures": 0, "phase_failures": 0,
              "arbitrary_target": "one seeded random target for each of4096 inputs",
              "seconds": time.monotonic() - start}
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
