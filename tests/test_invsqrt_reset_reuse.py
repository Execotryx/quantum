from importlib import import_module

from qcompile.invsqrt.scratch import ScratchProof


def test_reset_delimited_scratch_reuse_preserves_public_input(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    reuse = import_module("invsqrt_reset_reuse").reuse
    heading = [*(f"APPEND_TO_REGISTER q{q} r0\n" for q in range(22)), 'REGISTER r0 "x"\n']
    operations = [
        "CX q0 q31\n",
        "HMR q31 b0\n",
        "PUSH_CONDITION if b0\n",
        "Z q0\n",
        "CX q1 q35\n",
        "HMR q35 b1\n",
        "POP_CONDITION\n",
        "CX q2 q36\n",
        "CX q35 q36\n",
    ]
    result, report = reuse(heading + operations)
    assert result[:len(heading)] == heading
    assert result[len(heading):] == [
        "CX q0 q22\n",
        "HMR q22 b0\n",
        "PUSH_CONDITION if b0\n",
        "Z q0\n",
        "CX q1 q22\n",
        "HMR q22 b1\n",
        "POP_CONDITION\n",
        "CX q2 q23\n",
        "CX q22 q23\n",
    ]
    assert report == {"original_width": 37, "width": 24, "released_scratch_intervals": 1}


def test_symbolic_reversal_requires_matching_measurement_branch():
    proof = ScratchProof(input_width=2)
    assert not proof.step(["CCX", "q0", "q1", "q22"])
    assert not proof.step(["HMR", "q23", "b0"])
    assert not proof.step(["CCX", "q0", "q1", "q22", "if", "b0"])
    assert proof.values["q22"]
    assert not proof.step(["CCX", "q0", "q1", "q22", "if", "b0"])
    assert not proof.step(["CCX", "q1", "q0", "q22"])
    assert not proof.values["q22"]
    assert proof.step(["Z_POW", "q22", "0.125"])


def test_shared_phase_predicate_and_measurement_order(project_root, monkeypatch):
    proof = ScratchProof(input_width=2)
    proof.step(["CCX", "q0", "q1", "q2"])
    assert proof.shared_product(["CCX", "q0", "q1", "q3"], range(4)) == ["CX", "q2", "q3"]
    assert proof.shared_product(["CCZ", "q1", "q0", "q2"], range(4)) == ["Z", "q2"]
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    advance = import_module("invsqrt_reset_reuse").advance_resets
    lines = ["X q22\n", "X q23\n", "HMR q22 b0\n", "X q24\n", "HMR q23 b1\n"]
    assert advance(lines) == ([lines[i] for i in (0, 2, 1, 4, 3)], 2)


def test_named_input_is_only_lent_between_proven_zero_boundaries(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    lend = import_module("invsqrt_reset_reuse").lend_zeroed_inputs
    heading = [*(f"APPEND_TO_REGISTER q{q} r0\n" for q in range(22)), 'REGISTER r0 "x"\n']
    lines = ["SWAP q0 q22\n", "CX q1 q23\n", "Z q23\n", "CX q1 q23\n", "SWAP q0 q22\n"]
    output, stats = lend(heading + lines)
    assert output[:len(heading)] == heading
    assert output[len(heading):] == [lines[0], "CX q1 q0\n", "Z q0\n", "CX q1 q0\n", lines[-1]]
    assert stats["width"] == stats["interval_peak"] == 23
