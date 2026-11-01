"""Process boundary for the actual pinned notebook. Invoked only by official.py."""

import csv
import importlib
import os
import resource
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from .artifacts import validate_manifest
from .io import read_json, write_json
from .official import validate_backend
from .profiling import recorder
from .reference.scoring import finite_positive


def jsonable(value):
    import numpy as np

    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise ValueError(f"unsupported official result type: {type(value).__name__}")


def mapped_value(result, path):
    for component in path.split("."):
        result = result[component]
    value = jsonable(result)
    if type(value) is not int or value < 0:
        raise ValueError("mapped coverage counter must be a nonnegative actual integer")
    return value


def mapped_coverage(results, mapping):
    return {
        benchmark: {key: mapped_value(results[benchmark], path) for key, path in paths.items()}
        for benchmark, paths in mapping.items()
    }


def mapped_confirmation(results, mapping):
    if mapping is None:
        return None
    result = results[mapping["benchmark"]]
    count_fields = mapping["k"]
    if isinstance(count_fields, list):
        if not count_fields or len(set(count_fields)) != len(count_fields):
            raise ValueError("confirmation failure fields must be nonempty and distinct")
        failures = sum(mapped_value(result, path) for path in count_fields)
    else:
        failures = mapped_value(result, count_fields)
    observed = {"n": mapped_value(result, mapping["n"]), "k": failures}
    if observed["k"] > observed["n"]:
        raise ValueError("confirmation failures exceed completed shots")
    return observed


def main():
    profile = recorder()
    request = read_json(Path(sys.argv[1]))
    backend = request["backend"]
    with profile.stage("worker_input_integrity", "hashing", benchmark="all"):
        validate_backend(backend)
        validate_manifest(request["artifacts"])
    for role in ("kickmix", "verifiers"):
        sys.path.insert(0, str(Path(backend[role + "_root"]).resolve()))
    with profile.stage("metric_notebook_loading", "parsing", benchmark="all"):
        notebook = read_json(Path(backend["metric_notebook"]))
        source = "\n\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
        scope: dict[str, Any] = {"__name__": "qcompile_pinned_official_metric"}
        exec(compile(source, backend["metric_notebook"], "exec"), scope)
    root = Path.cwd()
    inputs = root / "evaluation_inputs"
    inputs.mkdir()
    scope["EVAL_INPUTS_DIR"] = inputs
    scope["KICKMIX_DIR"] = backend["kickmix_root"]
    scope["VERIFIERS_DIR"] = backend["verifiers_root"]
    divisor = 1 if request["tier"] == "full" else 1024
    write_json(inputs / "metadata.json", {"Hyperparameters": {"verification_shot_divisor": divisor}})
    with (inputs / "solution.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["row_id", "benchmark", "Usage", "seed_salt"])
        writer.writeheader()
        for index, benchmark in enumerate(("invsqrt", "dqi", "dfthcsos")):
            writer.writerow(
                {
                    "row_id": index,
                    "benchmark": benchmark,
                    "Usage": "Public",
                    "seed_salt": request["seed_policy"]["salt"],
                }
            )
    submission = root / "submission"
    submission.mkdir()
    with profile.stage("reference_artifact_copy", "copying", benchmark="all"):
        for name, record in request["artifacts"].items():
            path = submission / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(record["path"], path)
    if profile.directory is not None:
        for reader_name in ("read_circuit", "read_npz"):
            original_reader = scope[reader_name]

            def observed_reader(path, *args, _reader=original_reader, **kwargs):
                path = Path(path)
                benchmark = path.stem if path.stem in {"invsqrt", "dqi"} else "dfthcsos"
                with profile.stage(
                    f"parse:{path.name}", "parsing", benchmark=benchmark, input_bytes=path.stat().st_size
                ):
                    return _reader(path, *args, **kwargs)

            scope[reader_name] = observed_reader
    # Observe real return dictionaries without replacing any verifier arithmetic.
    raw_results = {}
    for benchmark, module_name in {
        "invsqrt": "invsqrt.verify_submission_invsqrt",
        "dqi": "dqi.verify_submission_dqi",
        "dfthcsos": "dfthcsos.verify",
    }.items():
        module = importlib.import_module(module_name)
        module_file = module.__file__
        if module_file is None or not Path(module_file).resolve().is_relative_to(
            Path(backend["verifiers_root"]).resolve()
        ):
            raise ValueError(f"verifier import escaped pinned source root: {module_name}")
        original = module.verify
        if profile.directory is not None:
            helpers = {
                "invsqrt": [
                    ("_circuit_sha256", "hashing"),
                    ("reference_values", "targets"),
                    ("_run_parallel", "simulation"),
                    ("rotation_t_count", "scoring"),
                ],
                "dqi": [
                    ("_circuit_sha256", "hashing"),
                    ("_run_parallel", "simulation"),
                    ("clopper_pearson_upper_bound", "scoring"),
                    ("repetition_overhead", "scoring"),
                ],
                "dfthcsos": [
                    ("submission_sha256", "hashing"),
                    ("load_inputs", "reference_loading"),
                    ("recover_words_from_circuits", "simulation"),
                    ("evaluate_words", "scoring"),
                    ("resource_costs", "scoring"),
                ],
            }[benchmark]
            for helper_name, category in helpers:
                setattr(
                    module,
                    helper_name,
                    profile.wrap(
                        getattr(module, helper_name),
                        f"{category}:{benchmark}:{helper_name}",
                        category,
                        benchmark=benchmark,
                    ),
                )

        def observe(*args, _original=original, _benchmark=benchmark, **kwargs):
            started = time.monotonic()
            with profile.stage(f"verify:{_benchmark}", "verification", benchmark=_benchmark):
                actual = _original(*args, **kwargs)
            raw_results[_benchmark] = actual
            write_json(
                root / f"benchmark-{_benchmark}.json",
                {
                    "kind": "official_benchmark_execution",
                    "benchmark": _benchmark,
                    "elapsed_seconds": time.monotonic() - started,
                    "result": jsonable(actual),
                    "claim": "actual verifier return; overall metric completion is recorded separately",
                },
            )
            print(f"official benchmark completed: {_benchmark}", flush=True)
            return actual

        setattr(module, "verify", observe)
    kickmix = importlib.import_module("kickmix")
    kickmix_file = kickmix.__file__
    if kickmix_file is None or not Path(kickmix_file).resolve().is_relative_to(
        Path(backend["kickmix_root"]).resolve()
    ):
        raise ValueError("kickmix import escaped pinned backend root")
    # Official reader, preflight, full traversal, scoring, exception behavior.
    with profile.stage("official_metric", "orchestration", benchmark="all"):
        scope["generate_standard_submission"](str(submission))
    with (root / "submission.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 3 or {int(row["row_id"]) for row in rows} != {0, 1, 2}:
        raise ValueError("official metric did not produce exactly three results")
    names = ("invsqrt", "dqi", "dfthcsos")
    costs = {names[int(row["row_id"])]: finite_positive(float(row["cost"]), "official cost") for row in rows}
    write_json(
        root / "worker-result.json",
        {
            "completed": True,
            "costs": costs,
            "verification_shot_divisor": divisor,
            "max_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "rss_units": "bytes on macOS, KiB on Linux",
            "pid": os.getpid(),
            "claim": "sampled circuit acceptance under local salt and official metric; no coherent proof",
            "raw_verifier_results": jsonable(raw_results),
            "coverage_counts": mapped_coverage(raw_results, backend.get("coverage_mapping", {})),
            "confirmation_observed": mapped_confirmation(raw_results, backend.get("confirmation_mapping")),
            "counts_note": "Counters require explicit source-reconciled mappings into real verifier returns.",
        },
    )


if __name__ == "__main__":
    main()
