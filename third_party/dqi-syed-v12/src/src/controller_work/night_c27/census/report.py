#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Audit a C2.7 state; incomplete or validation runs can never certify the plan."""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read_state(path):
    with Path(path).open() as stream:
        assert stream.readline().strip() == "DQI_C27_STATE_V1"
        digest = stream.readline().strip()
        mode, seed, draws = stream.readline().split()
        random_state = stream.readline().split()
        reasons = [list(map(int, stream.readline().split())) for _ in range(36)]
        nslots = [list(map(int, stream.readline().split())) for _ in range(36)]
        dslots = [list(map(int, stream.readline().split())) for _ in range(36)]
        profile_count = int(stream.readline())
        profiles = [list(map(int, stream.readline().split())) for _ in range(profile_count)]
        witness_count = int(stream.readline())
        witnesses = [list(map(int, stream.readline().split())) for _ in range(witness_count)]
        assert not stream.read().strip()
    draws = int(draws)
    assert len(random_state) == 313
    assert all(len(row) == 64 for row in reasons)
    assert all(len(row) == 35 for row in nslots+dslots)
    assert sum(map(sum, reasons)) == draws == sum(row[2] for row in profiles)
    assert sum(map(sum, nslots)) == sum(row[k] for row in reasons for k in range(64) if k & 1)
    assert sum(map(sum, dslots)) == sum(row[k] for row in reasons for k in range(64) if k & 2)
    assert len(witnesses) <= 64
    assert all(len(row) == 4+2*row[1] for row in witnesses)
    return dict(digest=digest, mode=mode, seed=int(seed), draws=draws,
                reasons=reasons, nslots=nslots, dslots=dslots,
                profiles=profiles, witnesses=witnesses)


def logcdf(k, n, p):
    if p <= 0:
        return 0.0
    if p >= 1:
        return 0.0 if k == n else -math.inf
    term = n*math.log1p(-p)
    total = term
    ratio = math.log(p)-math.log1p(-p)
    for i in range(1, k+1):
        term += math.log(n-i+1)-math.log(i)+ratio
        top, bottom = max(total, term), min(total, term)
        total = top+math.log1p(math.exp(bottom-top))
    return total


def cp_upper(k, n, log_delta):
    if n == 0 or k == n:
        return 1.0
    if k == 0:
        return -math.expm1(log_delta/n)
    if k > 100_000:
        from scipy.special import betainccinv
        return float(betainccinv(k+1, n-k, math.exp(log_delta)))
    lo = k/n
    hi = min(1.0, max((k+1)/n, 1e-8))
    while hi < 1 and logcdf(k, n, hi) > log_delta:
        hi = min(1.0, 2*hi)
    for _ in range(90):
        mid = (lo+hi)/2
        if logcdf(k, n, mid) > log_delta:
            lo = mid
        else:
            hi = mid
    return hi


def summarize(state_path, config_path, *, verify_sources=True):
    s = read_state(state_path)
    config = json.loads(Path(config_path).read_text())
    payload = config["payload"]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == s["digest"] == config["configuration_digest"]
    if verify_sources:
        for relative, expected in payload["source_sha256"].items():
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == expected, relative
    tv = float(Fraction(payload["total_variation_upper_exact"]))
    log_delta = -128*math.log(2)-math.log(3)
    completed = (s["mode"] == "production" and s["seed"] == payload["production_seed"]
                 and s["draws"] == payload["planned_draws"])
    reports = {}
    for cutoff in payload["precommitted_cutoffs"]:
        failures = sum(count for j, row in enumerate(s["reasons"])
                       for mask, count in enumerate(row) if j < cutoff or mask)
        upper = cp_upper(failures, s["draws"], log_delta)
        official_upper = min(1.0, upper+tv)
        status = ("COMPLETE_EVENT_BOUND_WITHIN_1E-5" if official_upper <= 1e-5 else
                  "COMPLETE_EVENT_BOUND_EXCEEDS_1E-5") if completed else "INCOMPLETE_NO_CERTIFICATE"
        reports[str(cutoff)] = dict(actual_n=s["draws"], union_failures=failures,
                                    cp_upper_sampled_law=upper,
                                    official_law_upper_with_tv=official_upper,
                                    confidence_delta_exact=payload["confidence_delta_per_cutoff_exact"],
                                    status=status)
    return dict(schema="DQI_C27_REPORT_V1", configuration_digest=digest,
                state_sha256=hashlib.sha256(Path(state_path).read_bytes()).hexdigest(),
                mode=s["mode"], seed=s["seed"], actual_draws=s["draws"],
                planned_draws=payload["planned_draws"], fixed_plan_completed=completed,
                claim="Classical event certificate only; native circuit inclusion, phase, restoration and official verifier remain separate.",
                confidence_assumption="Ideal independent interpretation of the precommitted deterministic mt19937_64 stream.",
                cutoff_reports=reports, total_variation_upper=tv,
                weight_histogram=list(map(sum, s["reasons"])),
                joint_reason_histogram=s["reasons"],
                first_finite_n_zero_by_weight_and_slot=s["nslots"],
                first_finite_d_zero_by_weight_and_slot=s["dslots"],
                full_half_degree_profile_histogram=s["profiles"],
                witnesses=s["witnesses"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.state, args.config)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps({k: result[k] for k in ("mode", "actual_draws", "planned_draws",
                                           "fixed_plan_completed", "cutoff_reports")}, sort_keys=True))
