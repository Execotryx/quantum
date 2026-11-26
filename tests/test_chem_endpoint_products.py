import sys
from importlib import import_module

import numpy as np
import pytest


def test_endpoint_proof_replaces_only_equal_product(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    rewrite = import_module("chem_endpoint_products").rewrite
    header = [
        "APPEND_TO_REGISTER q0 r0\n", "APPEND_TO_REGISTER q1 r0\n", 'REGISTER r0 "selection"\n',
        "APPEND_TO_REGISTER q2 r1\n", 'REGISTER r1 "word_0"\n',
    ]
    words = np.array([[0], [0], [0], [1]], dtype=np.int64)
    operations = ["CCX q0 q1 q3\n", "CCX q1 q0 q2\n", "HMR q3 b0\n", "CZ q0 q1 if b0\n"]
    actual, record = rewrite(header + operations, words, 0)
    assert actual == header + [operations[0], "CX q3 q2\n", *operations[2:]]
    assert record == {"eliminated": 0, "replaced_by_clifford": 1, "endpoint_rows": 8}
    with pytest.raises(ValueError, match="endpoint"):
        rewrite(header + operations, np.zeros((4, 1), dtype=np.int64), 0)


def test_endpoint_span_preserves_product_value_and_measurement_guard(project_root, monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    rewrite = import_module("chem_endpoint_products").rewrite
    header = [
        "APPEND_TO_REGISTER q0 r0\n", "APPEND_TO_REGISTER q1 r0\n", 'REGISTER r0 "selection"\n',
        "APPEND_TO_REGISTER q2 r1\n", 'REGISTER r1 "word_0"\n',
    ]
    words = np.array([[0], [0], [0], [0]], dtype=np.int64)
    operations = [
        "HMR q5 b0\n", "CCX q0 q1 q3\n", "CX q0 q3\n", "CCX q0 q1 q4\n",
        "CCZ q0 q1 q4 if b0\n", "CX q3 q4\n", "CX q0 q4\n",
        "CX q0 q3\n", "HMR q3 b1\n", "CZ q0 q1 if b1\n",
    ]
    actual, stats = rewrite(header + operations, words, 0, linear_span=True)
    assert actual == header + [
        *operations[:3], "CX q0 q4\n", "CX q3 q4\n", "Z q4 if b0\n", *operations[5:],
    ]
    assert stats["replaced_by_clifford"] == 2
    assert stats["screened_products"] == 3
    if sys.platform.startswith("linux") and (project_root / "vendor/backend.json").is_file():
        monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
        km = import_module("kickmix")
        values = np.arange(256) % 4
        bits = ((values >> np.arange(2)[:, None]) & 1).astype(bool)
        phases = []
        charges = []
        for label, lines in (("original", header + operations), ("rewrite", actual)):
            assembly = tmp_path / f"{label}.kmx"
            assembly.write_text("".join(lines), encoding="ascii")
            circuit = km.Circuit.from_file(assembly, format="kmx")
            sim = km.Simulator(batch_size=len(values), seed=36915, counting_operations=True)
            sim.use_same_registers_as(circuit)
            selection = circuit.register_data["selection"]
            sim.write_across_shots(selection, bits)
            sim.do(circuit)
            np.testing.assert_array_equal(sim.read_across_shots(selection), bits)
            scratch = km.array([km.q(i) for i in range(2, circuit.num_qubits)])
            assert not sim.read_across_shots(scratch).any()
            phases.append(sim.read_phase_flipped_across_shots())
            charges.append(sim.operation_statistics().num_toffoli_like)
        np.testing.assert_array_equal(*phases)
        assert phases[0].any() and not phases[0][values != 3].any()
        assert charges[1] < charges[0]
