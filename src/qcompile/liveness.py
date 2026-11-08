"""Observe public builder allocations without changing the emitted circuit.

Native builder methods may allocate and release internal workspace before they return;
those transient allocations are invisible to the public allocation counter. A capped
replay identifies the first call exceeding a given total-width bound.
"""

import inspect
from collections import Counter
from typing import Any, cast


class LivenessBuilder:
    def __init__(self, builder: Any):
        self.builder = builder
        self.live: dict[int, tuple[str, int]] = {}
        self.peak = 0
        self.peak_event: dict[str, Any] = {}
        self.failed_event: dict[str, Any] | None = None
        self.calls = 0

    @staticmethod
    def _path() -> list[str]:
        result: list[str] = []
        frame = inspect.currentframe()
        frame = frame.f_back.f_back if frame and frame.f_back else None
        while frame is not None:
            filename = frame.f_code.co_filename.replace("\\", "/")
            if not filename.endswith("/liveness.py") and (
                "/qcompile/" in filename or filename.endswith("nr_reference_circuit.py")
            ):
                result.append(f"{filename.split('/')[-1]}:{frame.f_code.co_name}:{frame.f_lineno}")
            frame = frame.f_back
        return result

    def _event(self, name: str) -> dict[str, Any]:
        groups = Counter(self.live.values())
        return {"method": name, "allocated": self.builder.num_allocated_qubits,
                "path": self._path(),
                "live_allocations": [{"site": site, "width": width, "qubits": count}
                                     for (site, width), count in sorted(groups.items())]}

    def __getattr__(self, name: str) -> Any:
        member = getattr(self.builder, name)
        if not callable(member):
            return member

        def call(*args: Any, **kwargs: Any) -> Any:
            try:
                result = cast(Any, member(*args, **kwargs))
            except Exception:
                self.failed_event = self._event(name)
                raise
            self.calls += 1
            if name in ("alloc_qubits", "create_quantum_register"):
                path = self._path()
                site = path[0] if path else "external"
                width = len(result)
                for qubit in result:
                    self.live[qubit.id] = (site, width)
            elif name == "free":
                for qubit in args[0]:
                    self.live.pop(qubit.id, None)
            allocated = self.builder.num_allocated_qubits
            if allocated > self.peak:
                self.peak = allocated
                self.peak_event = self._event(name)
            return result
        return call


def operation_intervals(lines: Any, declared: int) -> dict[str, Any]:
    """Summarize first-to-last-use intervals, conservatively without splitting resets."""
    import re

    intervals: dict[int, list[int]] = {}
    resets: dict[int, list[int]] = {}
    operation = 0
    for line in lines:
        parts = line.strip().split()
        if not parts or parts[0] in ("APPEND_TO_REGISTER", "REGISTER", "INFO_TAG"):
            continue
        ids = {int(value) for value in re.findall(r"\bq(\d+)\b", line)}
        for qubit in ids:
            if qubit not in intervals:
                intervals[qubit] = [operation, operation]
            intervals[qubit][1] = operation
            if parts[0] in ("R", "HMR"):
                resets.setdefault(qubit, []).append(operation)
        operation += 1
    changes: Counter[int] = Counter()
    for first, last in intervals.values():
        changes[first] += 1
        changes[last + 1] -= 1
    active = peak = 0
    for index in sorted(changes):
        active += changes[index]
        peak = max(peak, active)
    return {"declared": declared, "max_id_plus_one": max(intervals, default=-1) + 1,
            "distinct_ids": len(intervals), "maximum_interval_overlap": peak,
            "intervals": {str(q): span for q, span in sorted(intervals.items())},
            "resets": {str(q): points for q, points in sorted(resets.items())}}
