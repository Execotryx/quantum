#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Bounded, separate-seed infrastructure checks. Run only under the root guard."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import prepare_config
import reference as R
import report

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, expect=0):
    started = time.monotonic()
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True)
    log.write_text(result.stdout+result.stderr)
    assert result.returncode == expect, (command, result.returncode, log, result.stderr)
    return result.stdout, time.monotonic()-started


def source_reference():
    path = ROOT / "controller_work/night_converter/night_reference.py"
    spec = importlib.util.spec_from_file_location("source_night_reference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def physical_fixtures():
    cases = []
    for j in range(36):
        for trial in range(2):
            roots = [1+(37*k+101*trial+11) % 4095 for k in range(j)]
            values = [1+(251*k+97*j+trial) % 4095 for k in range(j)]
            cases.append((f"physical_j{j}_t{trial}", roots, values, None))
    for j in (3, 15, 16, 17, 35):
        roots = [1+(37*k+211) % 4095 for k in range(j)]
        for label, omega, expected in (("forced_N0", list(R.QUADRATICS[0]), (0, "N")),
                                      ("forced_D1", list(R.QUADRATICS[1]), (1, "D")),
                                      ("small_Omega", [1], None)):
            values = []
            for a in roots:
                derivative = 1
                for b in roots:
                    if b != a:
                        derivative = R.mul(derivative, a ^ b)
                au = a
                for c in R.KAPPAS:
                    au = R.mul(au, R.mul(a, a) ^ a ^ c)
                values.append(R.divide(R.evaluate(omega, a), R.mul(au, derivative)))
            actual, _ = R.physical_pair(roots, values)
            assert actual == omega
            cases.append((f"{label}_j{j}", roots, values, expected))
    return cases


def half_fixtures():
    profiles = [("ordinary", list(range(17, -1, -1)))]
    for start in range(2, 18):
        profiles.append((f"single_gap{start}", [x for x in range(17, -1, -1) if x != start-1]))
    profiles += [
        ("window17", [x for x in range(17, -1, -1) if x not in (16, 14)]),
        ("window14", [x for x in range(17, -1, -1) if x not in (13, 11)]),
        ("overlapping_window_requests_force_drop3", [x for x in range(17, -1, -1) if x not in (16, 14, 13, 11)]),
        ("drop3", [x for x in range(17, -1, -1) if x not in (16, 15)]),
        ("nonconstant_gcd", list(range(16, -1, -1))),
    ]
    out = []
    for label, degrees in profiles:
        current, following = [1], []
        for pos in range(len(degrees)-2, -1, -1):
            gap = degrees[pos]-degrees[pos+1]
            quotient = [((173*pos+97*k+1) % 4095)+1 for k in range(gap)]+[1]
            current, following = R.add(R.product(quotient, current), following), current
        a, b = current, following
        if label == "nonconstant_gcd":
            a, b = R.product(a, [1, 1]), R.product(b, [1, 1])
        d = [0]*36
        for k, value in enumerate(a):
            d[2*k+1] = R.mul(value, value)
        for k, value in enumerate(b):
            d[2*k] = R.mul(value, value)
        assert len(a) == 18 and d[-1]
        out.append((label, d))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=1000)
    parser.add_argument("--differential", type=int, default=128)
    args = parser.parse_args()
    assert 1 <= args.sample <= 100_000
    assert 1 <= args.differential <= min(args.sample, 10_000)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert not (out / "continuous.state").exists(), "Use a new validation output directory"
    cfg = prepare_config.build(out / "config")
    config = out / "config/config.txt"
    binary = out / "census"
    run(["g++", "-O3", "-std=c++17", "-Wall", "-Wextra", "-Werror", HERE / "census.cpp", "-o", binary], out / "compile.log")
    independent = source_reference()
    fixtures = physical_fixtures()
    cases_file = out / "physical_cases.txt"
    cases_file.write_text("".join(str(len(roots))+" "+" ".join(f"{a} {e}" for a, e in zip(roots, values))+"\n"
                                  for _, roots, values, _ in fixtures))
    stdout, _ = run([binary, "--cases", cases_file], out / "physical_native.jsonl")
    native_rows = [json.loads(line) for line in stdout.splitlines()]
    assert len(native_rows) == len(fixtures)
    reason_cases = {}
    for item, (label, roots, values, expected) in zip(native_rows, fixtures):
        scalar = R.classify(roots, values, include_polynomials=True)
        native = item["classification"]
        for key in native:
            assert native[key] == scalar[key], (label, key, native[key], scalar[key])
        d = scalar["padded_locator"]
        assert independent.profile(d) == scalar["half"]["degrees"]
        assert independent.admitted(d) == scalar["half"]["admitted"]
        if expected:
            assert (scalar["finite"]["slot"], scalar["finite"]["kind"]) == expected
        reason_cases[label] = scalar["reason_mask"]
    denominators = half_fixtures()
    denominator_file = out / "denominator_cases.txt"
    denominator_file.write_text("".join("36 "+" ".join(map(str, d))+"\n" for _, d in denominators))
    stdout, _ = run([binary, "--denominators", denominator_file], out / "half_native.jsonl")
    native_rows = [json.loads(line) for line in stdout.splitlines()]
    assert len(native_rows) == len(denominators)
    half_cases = {}
    for item, (label, d) in zip(native_rows, denominators):
        actual = item["classification"]["half"]
        assert actual == R.half_profile(d)
        assert independent.profile(d) == actual["degrees"]
        assert independent.admitted(d) == actual["admitted"]
        half_cases[label] = actual
    assert half_cases["window17"]["reason_mask"] & R.WINDOW17
    assert half_cases["window14"]["reason_mask"] & R.WINDOW14
    assert half_cases["drop3"]["reason_mask"] & R.DROP
    assert half_cases["nonconstant_gcd"]["reason_mask"] & R.GCD
    common = [binary, "--config", config, "--mode", "validation", "--seed", "202611111515",
              "--save-every", "1000"]
    continuous = out / "continuous.state"
    audit = out / "sample_audit.jsonl"
    stdout, elapsed = run(common+["--state", continuous, "--draws", args.sample,
                                 "--audit", audit, "--audit-limit", args.differential],
                          out / "continuous.log")
    timing = json.loads(stdout)
    split = out / "split.state"
    first = args.sample//3
    run(common+["--state", split, "--draws", first], out / "split_first.log")
    run(common+["--state", split, "--draws", args.sample-first], out / "split_second.log")
    assert continuous.read_bytes() == split.read_bytes(), "Resume changed PRNG stream or counters"
    differential = 0
    for line in audit.read_text().splitlines():
        item = json.loads(line)
        scalar = R.classify(item["roots"], item["values"])
        assert item["classification"] == scalar, (item["draw"], item["classification"], scalar)
        differential += 1
    assert differential == args.differential
    state = report.read_state(continuous)
    for row in state["witnesses"]:
        _, j, reason, profile = row[:4]
        scalar = R.classify(row[4::2], row[5::2])
        assert scalar["weight"] == j and scalar["reason_mask"] == reason
        assert scalar["half"]["degree_mask"] == profile
    # Rejection gates create no production draws.
    run([binary, "--config", config, "--mode", "production", "--seed", "123", "--state", out / "invalid.state", "--draws", "0"],
        out / "reject_seed.log", expect=1)
    run([binary, "--config", config, "--mode", "production", "--seed", "202611112245", "--state", out / "invalid.state", "--draws", "500000001"],
        out / "reject_excess.log", expect=1)
    assert not (out / "invalid.state").exists()
    bad_state = out / "bad_digest.state"
    bad_state.write_text(continuous.read_text().replace(cfg["configuration_digest"], "0"*64, 1))
    run(common+["--state", bad_state, "--draws", "0"], out / "reject_digest.log", expect=1)
    summary = report.summarize(continuous, out / "config/config.json")
    assert not summary["fixed_plan_completed"]
    (out / "sample_report.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n")
    rate = args.sample / timing["seconds"]
    receipt = dict(status="PASS_BOUNDED_CLASSICAL_INFRASTRUCTURE_ONLY", production_draws=0,
                   configuration_digest=cfg["configuration_digest"],
                   physical_cases=len(fixtures), forced_finite_cases=10,
                   synthetic_half_profiles=len(denominators),
                   random_reference_replays=differential,
                   validation_draws=args.sample, resume_state_byte_identical=True,
                   native_seconds=timing["seconds"], subprocess_wall_seconds=elapsed,
                   draws_per_second=rate, projected_500m_seconds=500_000_000/rate,
                   projected_500m_hours=500_000_000/rate/3600,
                   validation_counts=timing, physical_reason_cases=reason_cases,
                   half_profile_cases=half_cases,
                   binary_sha256=sha(binary), continuous_state_sha256=sha(continuous),
                   sample_audit_sha256=sha(audit),
                   limitations=["Small validation is not a rare-event bound or official verifier run.",
                                "Throughput extrapolation is measured on this bounded batch; full sample has not run.",
                                "SIGTERM save is implemented but this harness only checks ordinary split/resume."])
    (out / "validation.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    print(json.dumps({k: receipt[k] for k in ("status", "physical_cases", "synthetic_half_profiles",
                                             "random_reference_replays", "validation_draws", "draws_per_second",
                                             "projected_500m_hours", "production_draws")}, sort_keys=True))


if __name__ == "__main__":
    main()
