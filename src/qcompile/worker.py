"""Process boundary for the actual pinned notebook. Invoked only by official.py."""

import csv
import importlib
import os
import resource
import shutil
import sys
from pathlib import Path

from .artifacts import validate_manifest
from .io import read_json, write_json
from .official import validate_backend
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
    return {key: mapped_value(results[mapping["benchmark"]], mapping[key]) for key in ("n", "k")}


def main():
    request = read_json(Path(sys.argv[1]))
    backend = request["backend"]
    validate_backend(backend)
    validate_manifest(request["artifacts"])
    for role in ("kickmix", "verifiers"):
        sys.path.insert(0, str(Path(backend[role + "_root"]).resolve()))
    notebook = read_json(Path(backend["metric_notebook"]))
    source = "\n\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    scope = {"__name__": "qcompile_pinned_official_metric"}
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
    for name, record in request["artifacts"].items():
        path = submission / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(record["path"], path)
    # Observe real return dictionaries without replacing any verifier arithmetic.
    raw_results = {}
    for benchmark, module_name in {
        "invsqrt": "invsqrt.verify_submission_invsqrt",
        "dqi": "dqi.verify_submission_dqi",
        "dfthcsos": "dfthcsos.verify",
    }.items():
        module = importlib.import_module(module_name)
        if not Path(module.__file__).resolve().is_relative_to(Path(backend["verifiers_root"]).resolve()):
            raise ValueError(f"verifier import escaped pinned source root: {module_name}")
        original = module.verify

        def observe(*args, _original=original, _benchmark=benchmark, **kwargs):
            actual = _original(*args, **kwargs)
            raw_results[_benchmark] = actual
            return actual

        module.verify = observe
    kickmix = importlib.import_module("kickmix")
    if not Path(kickmix.__file__).resolve().is_relative_to(Path(backend["kickmix_root"]).resolve()):
        raise ValueError("kickmix import escaped pinned backend root")
    # Official reader, preflight, full traversal, scoring, exception behavior.
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
