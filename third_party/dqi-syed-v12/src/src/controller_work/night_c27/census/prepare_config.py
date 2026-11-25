#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Pin the precommitted C2.7 law and source. This script makes no random draws."""
from __future__ import annotations

import argparse
import ast
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import reference as R

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "controller_work"
OFFICIAL = ROOT / "pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py"
CERTIFICATE = WORK / "work/round2/milestone132/logs/cutoff-budget.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out):
    cert = json.loads(CERTIFICATE.read_text())["certificate"]
    assert cert["matrix_size"] == 36 and cert["official_r"] == 2016
    assert sha(OFFICIAL) == cert["official_source_sha256"]
    assert cert["diagonal"] == "2*k"
    assert cert["off_diagonal_squared"] == "4095*k*(4096-k), k=1..35"
    vector = [Fraction(x) for x in cert["vector"]]
    norm = sum(x*x for x in vector)
    probabilities = [x*x/norm for x in vector]
    unit = 1 << 64
    thresholds = []
    cumulative = Fraction(0)
    for probability in probabilities[:-1]:
        cumulative += probability
        thresholds.append((unit*cumulative).numerator // (unit*cumulative).denominator)
    edges = [0] + thresholds + [unit]
    quantized = [Fraction(b-a, unit) for a, b in zip(edges, edges[1:])]
    quantization_tv = sum(abs(p-q) for p, q in zip(probabilities, quantized))/2
    assert quantization_tv <= Fraction(35, unit)
    spectral_tv = Fraction(cert["total_variation_upper_exact"])
    paths = [HERE / name for name in (
        "AMENDMENT_V1.md", "reference.py", "census.cpp", "prepare_config.py",
        "validate.py", "report.py")]
    paths += [OFFICIAL, CERTIFICATE,
              WORK / "night_converter/night_reference.py",
              WORK / "night_converter/night_outer.py"]
    native = WORK / "work/round2/milestone152/source"
    paths += [native / name for name in (
        "raw_gap2_bezout.py", "raw_lower_window.py", "raw_window_tensor.py",
        "raw_window_transpose.py")]
    source_hashes = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    payload = dict(
        schema="DQI_C27_CONFIG_V1", planned_draws=500_000_000,
        production_seed=202611112245, validation_seed=202611111515,
        confidence_delta_exact=str(Fraction(1, 1 << 128)),
        confidence_delta_per_cutoff_exact=str(Fraction(1, 3*(1 << 128))),
        primary_cutoff=15, precommitted_cutoffs=[15, 16, 17],
        field_modulus=R.MODULUS, extension_kappa=R.KAPPA,
        quadratic_kappas=list(R.KAPPAS),
        weight_probabilities_central_exact=list(map(str, probabilities)),
        weight_bin_upper_bounds=thresholds,
        quantized_weight_probabilities_exact=list(map(str, quantized)),
        spectral_total_variation_upper_exact=str(spectral_tv),
        quantization_total_variation_exact=str(quantization_tv),
        total_variation_upper_exact=str(spectral_tv+quantization_tv),
        full35_rejections=["nonconstant gcd", "degree drop > 2",
                           "drop-2 starts 17 and 15", "drop-2 starts 14 and 12"],
        finite_rejection="first active N mod q_i = 0 OR D mod q_i = 0",
        source_sha256=source_hashes,
        sampling_status="configuration only; zero sampler draws")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    official_comparison = {"status": "NUMERICAL_CROSSCHECK_NOT_RUN"}
    try:
        import numpy as np
        tree = ast.parse(OFFICIAL.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "optimal_dqi_weights")
        namespace = {"np": np, "math": math}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(OFFICIAL), "exec"), namespace)
        exact_official_function_result = namespace["optimal_dqi_weights"](4095, 35, 12, 2016)**2
        diff = sum(abs(float(p)-float(q)) for p, q in zip(probabilities, exact_official_function_result))/2
        assert diff < float(spectral_tv), (diff, spectral_tv)
        official_comparison = dict(status="NUMERICAL_FUNCTION_CROSSCHECK_PASS", total_variation_float=diff)
    except ImportError:
        pass
    report = dict(configuration_digest=digest, payload=payload,
                  numerical_official_comparison=official_comparison,
                  total_variation_upper_float=float(spectral_tv+quantization_tv),
                  weight_probabilities_float=list(map(float, probabilities)),
                  cutoff_masses={str(c): dict(central_exact=str(sum(probabilities[:c])),
                                              central_float=float(sum(probabilities[:c])),
                                              upper_with_spectral_tv=float(sum(probabilities[:c])+spectral_tv))
                                 for c in (15, 16, 17)})
    out.mkdir(parents=True, exist_ok=True)
    config_path = out / "config.txt"
    json_path = out / "config.json"
    config_path.write_text("DQI_C27_CONFIG_V1\n" + digest + "\n" +
                           "500000000 202611112245 4179 2048\n" +
                           " ".join(map(str, thresholds)) + "\n" +
                           " ".join(map(str, R.KAPPAS)) + "\n")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps(dict(status="CONFIGURATION_PINNED_NO_DRAWS", configuration_digest=digest,
                          config_sha256=sha(config_path), report_sha256=sha(json_path),
                          total_variation_upper=float(spectral_tv+quantization_tv),
                          official_comparison=official_comparison), sort_keys=True))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "config_v1")
    build(parser.parse_args().out)
