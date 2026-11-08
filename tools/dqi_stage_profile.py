"""Attribute the pinned DQI reference circuit's static cost to its marked stages."""

import argparse
import sys
import time
from collections import Counter
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import Any

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend

STAGES = {
    "initial_shift": "syndrome_prep",
    "forward_eea": "locator_forward",
    "chien_forney_mbuc": "scan",
    "reverse_eea": "locator_reverse",
    "uncompute_initial_shift": "cleanup",
}
CENSUS = {
    "ixor_gf2_mul", "init_gf2_div_with_scaffold", "del_gf2_div_with_scaffold",
    "init_gf2_inverse_with_scaffold", "del_gf2_inverse_with_scaffold", "cswap",
    "left_rotate", "right_rotate",
}
REFERENCE_METHODS = {
    "build_syndrome_decoding_mbuc", "_initial_shift_loop", "_synchronized_eea",
    "_counter_controls", "_del_counter_controls", "_update_counter", "_update_flag",
    "_multiply_and_add_or_sub", "accumulate_quotient", "sweep_positions", "endpoint",
    "_xor_threshold", "_shift_b_array_right", "_update_metadata", "_swap_a_and_b",
    "_update_halting_counter", "_pre_align_reg_b", "_chien_search_and_forney_mbuc",
}
LOCATOR_METHODS = REFERENCE_METHODS - {
    "build_syndrome_decoding_mbuc", "_initial_shift_loop", "_pre_align_reg_b",
    "_chien_search_and_forney_mbuc",
}
METHOD_STAGES = {name: {"locator_forward", "locator_reverse"} for name in LOCATOR_METHODS}
METHOD_STAGES.update({
    "build_syndrome_decoding_mbuc": {"syndrome_prep", "cleanup"},
    "_initial_shift_loop": {"syndrome_prep", "cleanup"},
    "_pre_align_reg_b": {"scan"},
    "_chien_search_and_forney_mbuc": {"scan"},
})
NESTED_MARKS = {
    "shift_step", "eea_step", "update_flag", "quotient_div", "sweep_positions",
    "multiply_and_add_or_sub", "shift_b_array_right", "update_metadata", "swap_a_and_b",
    "update_halting_counter", "pre_align_reg_b", "unalign_reg_b", "forney_step",
}


def snapshot(builder: Any) -> tuple[Counter, int]:
    circuit = builder.finish_circuit()
    stats = circuit.operation_statistics()
    return Counter(dict(stats)), int(stats.num_toffoli_like)


def difference(after: tuple[Counter, int], before: tuple[Counter, int]) -> dict:
    counts = after[0] - before[0]
    if any(after[0][name] < value for name, value in before[0].items()) or after[1] < before[1]:
        raise ValueError("builder statistics decreased")
    return {"operations": dict(sorted(counts.items())), "toffoli_like": after[1] - before[1]}


class StageProfileBuilder:
    """Observe boundary counts while delegating every emission to the native builder."""

    def __init__(self, builder: Any):
        self.builder = builder
        self.stage = "syndrome_prep"
        self.seen: list[str] = []
        self.records: dict[str, dict] = {}
        self.census: dict[str, Counter] = {s: Counter() for s in STAGES.values()}
        self.peak: dict[str, int] = {s: 0 for s in STAGES.values()}
        self.entry: dict[str, int] = {}
        self.last = snapshot(builder)

    def _live(self) -> int:
        return int(self.builder.num_allocated_qubits)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self.builder, name)
        if not callable(attr):
            return attr

        def call(*args: Any, **kwargs: Any) -> Any:
            caller = sys._getframe(1).f_code
            if (caller.co_filename.endswith("dqi_reference_circuit.py")
                    and self.stage not in METHOD_STAGES.get(caller.co_name, set())):
                raise ValueError(f"unmapped reference method/stage: {caller.co_name}/{self.stage}")
            if name in CENSUS:
                self.census[self.stage][name] += 1
            value = attr(*args, **kwargs)
            self.peak[self.stage] = max(self.peak[self.stage], self._live())
            return value
        return call

    def mark(self, name: str):
        if name not in STAGES:
            if name not in NESTED_MARKS:
                raise ValueError(f"unmapped reference mark: {name}")
            return self.builder.mark(name)
        return self._stage_mark(name)

    @contextmanager
    def _stage_mark(self, name: str):
        expected = list(STAGES)[len(self.seen)] if len(self.seen) < len(STAGES) else None
        if name != expected:
            raise ValueError(f"unexpected reference stage {name!r}; expected {expected!r}")
        before = snapshot(self.builder)
        gap = difference(before, self.last)
        if self.seen and (gap["operations"] or gap["toffoli_like"]):
            raise ValueError(f"unattributed emissions before {name}")
        if not self.seen:
            self.records["syndrome_prep"] = gap
        self.stage = STAGES[name]
        self.entry.setdefault(self.stage, self._live())
        self.peak[self.stage] = max(self.peak[self.stage], self._live())
        with self.builder.mark(name):
            yield
        after = snapshot(self.builder)
        delta = difference(after, before)
        if self.stage == "syndrome_prep":
            delta["operations"] = dict(Counter(delta["operations"]) + Counter(gap["operations"]))
            delta["toffoli_like"] += gap["toffoli_like"]
        self.records[self.stage] = delta
        self.last = after
        self.seen.append(name)

    def finish_profile(self) -> tuple[Any, dict]:
        if self.seen != list(STAGES):
            raise ValueError(f"incomplete or unmapped stage sequence: {self.seen}")
        circuit = self.builder.finish_circuit()
        stats = circuit.operation_statistics()
        final = (Counter(dict(stats)), int(stats.num_toffoli_like))
        tail = difference(final, self.last)
        cleanup = self.records["cleanup"]
        cleanup["operations"] = dict(Counter(cleanup["operations"]) + Counter(tail["operations"]))
        cleanup["toffoli_like"] += tail["toffoli_like"]
        if sum(record["toffoli_like"] for record in self.records.values()) != final[1]:
            raise ValueError("stage Toffoli totals do not reconcile")
        if sum((Counter(x["operations"]) for x in self.records.values()), Counter()) != final[0]:
            raise ValueError("stage operation counts do not reconcile")
        for stage, record in self.records.items():
            record.update(entry_live_qubits=self.entry.get(stage), peak_observed_live_qubits=self.peak[stage],
                          census=dict(sorted(self.census[stage].items())),
                          toffoli_share=record["toffoli_like"] / final[1] if final[1] else 0)
        return circuit, {"stages": self.records, "static_toffoli_like": final[1],
                         "static_operations": dict(sorted(final[0].items()))}


def profile(backend_path: Path, output: Path, *, m: int, n: int, control: Path | None) -> None:
    if not 2 <= n <= min(m, 70) or n % 2 or m > 4095:
        raise ValueError("require even syndrome count in [2, 70] and n <= m <= 4095")
    backend = read_json(backend_path)
    validate_backend(backend)
    official = Path(backend["verifiers_root"]) / "dqi"
    sys.path[:0] = [backend["kickmix_root"], str(official)]
    km = import_module("kickmix")
    ref = import_module("dqi_reference_circuit")
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    builder = StageProfileBuilder(km.CircuitBuilder())
    syndromes = [builder.create_quantum_register(12, name=f"S{i}") for i in range(n)]
    masks = [builder.create_classical_register(12, name=f"E{j}") for j in range(m)]
    ref.ProosAndZalkaDecoder(n, km.GF2Field(12)).build_syndrome_decoding_mbuc(
        builder, syndromes=syndromes, error_mbuc=masks, n_iters=ref.default_n_iters(n))
    circuit, result = builder.finish_profile()
    path = output / "profiled.kmb"
    circuit.to_file(str(path), format="kmb")
    digest = sha256(path)
    del circuit, builder
    reference = ref.build_reference_circuit(m, n, 12)
    reference_path = output / "reference.kmb"
    reference.to_file(str(reference_path), format="kmb")
    if digest != sha256(reference_path):
        raise ValueError("profiled circuit does not match reference bytes")
    result.update(m=m, n=n, degree=12, kmb_sha256=digest, declared_qubits=reference.num_qubits,
                  emitter_sha256=sha256(official / "dqi_reference_circuit.py"),
                  verifier_sha256=sha256(official / "verify_submission_dqi.py"),
                  elapsed_seconds=time.monotonic() - started,
                  width_note="observed after proxy calls only; excludes transient native allocations",
                  count_definition="pinned kickmix operation_statistics().num_toffoli_like, as used by verifier",
                  census_note="builder call counts, not expanded gates; native internal sites excluded")
    if control is not None:
        receipt = read_json(control)
        if receipt.get("kmb_sha256") != digest or receipt.get("m") != m or receipt.get("n") != n:
            raise ValueError("control receipt does not identify these circuit bytes and shape")
        mean, maximum = receipt["toffoli_count"], receipt["max_toffoli_count"]
        residual = result["static_toffoli_like"] - mean
        result["executed_reconciliation"] = {"mean": mean, "maximum": maximum, "residual": residual,
                                               "within_observed_spread": abs(residual) <= maximum - mean,
                                               "receipt_sha256": sha256(control)}
    write_json(output / "stage-profile.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--control", type=Path)
    args = parser.parse_args()
    profile(args.backend, args.output, m=args.m, n=args.n, control=args.control)
