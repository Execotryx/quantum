"""Guard attribution boundaries and unknown reference marks."""

from contextlib import nullcontext

import pytest

from tools.dqi_stage_profile import STAGES, StageProfileBuilder


class Stats(dict):
    @property
    def num_toffoli_like(self):
        return self.get("CCX", 0)


class Circuit:
    def __init__(self, gates):
        self.gates = Stats(gates)

    def operation_statistics(self):
        return self.gates


class Builder:
    num_allocated_qubits = 0

    def __init__(self):
        self.gates = {}

    def finish_circuit(self):
        return Circuit(self.gates)

    def mark(self, _name):
        return nullcontext()

    def ccx(self):
        self.gates["CCX"] = self.gates.get("CCX", 0) + 1


def test_stage_counts_reconcile_and_gaps_fail():
    builder = StageProfileBuilder(Builder())
    for name in STAGES:
        with builder.mark(name):
            builder.ccx()
    _, record = builder.finish_profile()
    assert record["static_toffoli_like"] == 5
    assert [item["toffoli_like"] for item in record["stages"].values()] == [1] * 5
    builder = StageProfileBuilder(Builder())
    with builder.mark("initial_shift"):
        pass
    builder.ccx()
    with pytest.raises(ValueError, match="unattributed"):
        with builder.mark("forward_eea"):
            pass


def test_unknown_mark_and_incomplete_profile_fail():
    builder = StageProfileBuilder(Builder())
    with pytest.raises(ValueError, match="unmapped"):
        builder.mark("new_phase")
    with pytest.raises(ValueError, match="incomplete"):
        builder.finish_profile()
