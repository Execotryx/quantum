"""Opt-in stage observation and Linux process-tree sampling, outside verifier threads."""

import functools
import json
import os
import signal
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from .errors import ValidationError
from .io import write_json


def io_counters(pid: int) -> dict[str, int]:
    try:
        return {
            key: int(value)
            for line in Path(f"/proc/{pid}/io").read_text().splitlines()
            for key, value in [line.split(":", 1)]
        }
    except (OSError, ValueError):
        return {}


def process_stat(pid: int) -> dict[str, int] | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {"pid": pid, "parent": int(fields[1]), "start_ticks": int(fields[19])}
    except (OSError, ValueError, IndexError):
        return None


def process_tree(root_pid: int) -> dict[int, dict[str, int]]:
    found: dict[int, dict[str, int]] = {}
    pending = [root_pid]
    while pending:
        pid = pending.pop()
        if pid in found:
            continue
        stat = process_stat(pid)
        if stat is None:
            continue
        found[pid] = stat
        try:
            for task in Path(f"/proc/{pid}/task").iterdir():
                try:
                    pending.extend(map(int, (task / "children").read_text().split()))
                except (OSError, ValueError):
                    continue
        except OSError:
            continue
    return found


def proportional_memory(pid: int) -> dict[str, int] | None:
    try:
        values = {}
        for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
            key, _, value = line.partition(":")
            if key in {"Rss", "Pss", "SwapPss"}:
                values[key] = int(value.split()[0]) * 1024
        if not {"Rss", "Pss", "SwapPss"} <= values.keys():
            return None
        return values
    except (OSError, ValueError, IndexError):
        return None


def terminate_tree(root_pid: int) -> None:
    """Signal only the observed process identities; do not act on reused PIDs."""
    observed = process_tree(root_pid)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid, identity in reversed(list(observed.items())):
            current = process_stat(pid)
            if current is not None and current["start_ticks"] == identity["start_ticks"]:
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
        if sig == signal.SIGTERM:
            time.sleep(0.5)


def cpu_snapshot() -> dict[str, float]:
    times = os.times()
    return {
        "self_cpu_seconds": time.process_time(),
        "waited_children_cpu_seconds": times.children_user + times.children_system,
    }


class StageRecorder:
    def __init__(self, directory: Path | None):
        self.directory = directory
        self.pid = os.getpid()
        self.stack: list[dict[str, Any]] = []
        self.sequence = 0
        self.stream: Any = None
        if directory is not None:
            directory.mkdir(parents=True, exist_ok=True)
            self.stream = (directory / f"events-{self.pid}.jsonl").open("x", encoding="utf-8", buffering=1)

    def emit(self, event: dict[str, Any]) -> None:
        self.stream.write(json.dumps(event, allow_nan=False) + "\n")

    def current(self) -> None:
        if self.directory is not None:
            write_json(
                self.directory / f"current-{self.pid}.json",
                {
                    "pid": self.pid,
                    "identity": process_stat(self.pid),
                    "stage": self.stack[-1] if self.stack else None,
                },
                replace=True,
            )

    @contextmanager
    def stage(self, name: str, category: str, **attributes: Any) -> Iterator[None]:
        if self.directory is None:
            yield
            return
        self.sequence += 1
        frame = {
            "id": f"{self.pid}:{self.sequence}",
            "pid": self.pid,
            "name": name,
            "category": category,
            "parent_id": self.stack[-1]["id"] if self.stack else None,
            "start_ns": time.monotonic_ns(),
            **attributes,
        }
        before_cpu, before_io = cpu_snapshot(), io_counters(self.pid)
        self.stack.append(frame)
        self.emit({"event": "start", **frame})
        self.current()
        status = "passed"
        try:
            yield
        except BaseException as error:
            status = type(error).__name__
            raise
        finally:
            end_ns = time.monotonic_ns()
            after_cpu, after_io = cpu_snapshot(), io_counters(self.pid)
            self.emit(
                {
                    "event": "end",
                    **frame,
                    "end_ns": end_ns,
                    "status": status,
                    "wall_seconds_inclusive": (end_ns - frame["start_ns"]) / 1e9,
                    **{key: after_cpu[key] - value for key, value in before_cpu.items()},
                    "io_self_delta": {
                        key: after_io[key] - value for key, value in before_io.items() if key in after_io
                    },
                    "io_scope": "current process only; rchar/wchar logical, read_bytes/write_bytes storage-layer counters",
                }
            )
            self.stack.pop()
            self.current()

    def wrap(
        self, function: Callable[..., Any], name: str, category: str, **attributes: Any
    ) -> Callable[..., Any]:
        if self.directory is None:
            return function

        @functools.wraps(function)
        def observed(*args: Any, **kwargs: Any) -> Any:
            with self.stage(name, category, **attributes):
                return function(*args, **kwargs)

        return observed


_recorder: StageRecorder | None = None


def recorder() -> StageRecorder:
    global _recorder
    if _recorder is None or _recorder.pid != os.getpid():
        directory = os.environ.get("QCOMPILE_PROFILE_DIR")
        _recorder = StageRecorder(Path(directory) if directory else None)
    return _recorder


class ResourceSampler:
    def __init__(self, root_pid: int, directory: Path, interval: float):
        if not sys.platform.startswith("linux") or not 0.05 <= interval <= 10:
            raise ValidationError("process-tree profiling requires Linux and a sample interval in [0.05,10]")
        self.root_pid, self.directory, self.interval = root_pid, directory, interval
        identity = process_stat(root_pid)
        if identity is None:
            raise ValidationError("profile root process is unavailable")
        self.identity = identity
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name="qcompile-resource-sampler", daemon=True)
        self.error: str | None = None
        self.summary: dict[str, Any] = {
            "samples": 0,
            "missing_memory_reads": 0,
            "attempted_memory_reads": 0,
            "peak_pss_bytes": 0,
            "peak_summed_rss_bytes": 0,
            "peak_swap_pss_bytes": 0,
            "peak_pss_plus_swap_bytes": 0,
            "peak_process_count": 0,
            "by_stage": {},
            "by_benchmark": {},
            "interval_seconds": interval,
            "root_identity": self.identity,
            "memory_scope": "sampled live CLI process and descendants; PSS apportions shared pages; summed RSS double-counts sharing",
            "limitations": "sampled peaks can miss short events; processes can exit during a sample; WSL storage counters may not include host I/O",
        }

    def start(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.thread.join(timeout=30)
        if self.thread.is_alive():
            raise ValidationError("resource sampler did not stop")
        if self.error is not None:
            raise ValidationError(f"resource sampler failed: {self.error}")
        if self.summary["samples"] == 0 or self.summary["peak_pss_bytes"] <= 0:
            raise ValidationError("no resource samples were recorded")
        write_json(self.directory / "resources.json", self.summary)
        return self.summary

    def sample(self) -> dict[str, Any] | None:
        current = process_stat(self.root_pid)
        if current is None or current["start_ticks"] != self.identity["start_ticks"]:
            return None
        tree = process_tree(self.root_pid)
        totals = {"Pss": 0, "Rss": 0, "SwapPss": 0}
        missing = 0
        active = []
        for pid, stat in tree.items():
            memory = proportional_memory(pid)
            if memory is None:
                missing += 1
            else:
                for key in totals:
                    totals[key] += memory[key]
            try:
                state = json.loads((self.directory / f"current-{pid}.json").read_text())
                if state.get("identity") == stat and state.get("stage"):
                    active.append(state["stage"])
            except (OSError, ValueError):
                pass
        stage = (
            max(active, key=lambda item: item["start_ns"])
            if active
            else {"name": "startup_or_unattributed", "category": "orchestration"}
        )
        return {
            "monotonic_ns": time.monotonic_ns(),
            "process_count": len(tree),
            "missing_memory_reads": missing,
            "stage": stage,
            **totals,
        }

    def run(self) -> None:
        started = time.thread_time()
        first_sample: int | None = None
        last_sample: int | None = None
        try:
            with (self.directory / "samples.jsonl").open("x", encoding="utf-8", buffering=65536) as stream:
                while not self.stop_event.is_set():
                    sample = self.sample()
                    if sample is None:
                        break
                    if first_sample is None:
                        first_sample = sample["monotonic_ns"]
                    last_sample = sample["monotonic_ns"]
                    stream.write(json.dumps(sample, allow_nan=False) + "\n")
                    self.summary["samples"] += 1
                    self.summary["missing_memory_reads"] += sample["missing_memory_reads"]
                    self.summary["attempted_memory_reads"] += sample["process_count"]
                    stage_key = sample["stage"]["name"]
                    peak = self.summary["by_stage"].setdefault(stage_key, {"peak_pss_bytes": 0, "samples": 0})
                    peak["peak_pss_bytes"] = max(peak["peak_pss_bytes"], sample["Pss"])
                    peak["samples"] += 1
                    benchmark = sample["stage"].get("benchmark", "unattributed")
                    benchmark_peak = self.summary["by_benchmark"].setdefault(
                        benchmark, {"peak_pss_bytes": 0, "samples": 0}
                    )
                    benchmark_peak["peak_pss_bytes"] = max(benchmark_peak["peak_pss_bytes"], sample["Pss"])
                    benchmark_peak["samples"] += 1
                    self.summary["peak_pss_plus_swap_bytes"] = max(
                        self.summary["peak_pss_plus_swap_bytes"], sample["Pss"] + sample["SwapPss"]
                    )
                    for source, destination in (
                        ("Pss", "peak_pss_bytes"),
                        ("Rss", "peak_summed_rss_bytes"),
                        ("SwapPss", "peak_swap_pss_bytes"),
                        ("process_count", "peak_process_count"),
                    ):
                        self.summary[destination] = max(self.summary[destination], sample[source])
                    if self.summary["samples"] % 10 == 0:
                        stream.flush()
                        write_json(
                            self.directory / "progress.json",
                            {"pid": self.root_pid, "alive": True, **self.summary},
                            replace=True,
                        )
                    self.stop_event.wait(self.interval)
        except Exception as error:
            self.error = repr(error)
        finally:
            self.summary["profiler_cpu_seconds"] = time.thread_time() - started
            self.summary["observed_mean_interval_seconds"] = (
                (last_sample - first_sample) / 1e9 / (self.summary["samples"] - 1)
                if first_sample is not None and last_sample is not None and self.summary["samples"] > 1
                else None
            )
