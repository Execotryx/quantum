## Controls

| Archive | ZIP SHA-256 | Local pinned metric | Kaggle public | State |
| --- | --- | ---: | ---: | --- |
| v2 hybrid | `9aac7afcd0ff3bbff7f4c65c85cf1b331e67b3fd9893ec83b8499d0f223bb841` | 1.3779715418 | 1.37797 | Reconciled |
| v3 hybrid | `920fcfba647e59524d9f66b254d1fc6438e4fb792663524c16bac4453f0ac94d` | 1.5753293577 | pending | Expected 1.57533 |

The v2 receipt shows the uploaded file name `submission.zip` with no
description. Record it retroactively from the user's statement and the
score match, and mark its archive binding `inferred`. Every later
receipt binds the hash directly.
[v3 archive evidence](../../../docs/advance-hybrid-validation-08-11-2026-05-33-43.md)

## External receipt ledger

Store one JSON record per upload under `docs/evidence/kaggle/`, named
`<UTC date>-<zip sha256[:12]>.json`. Never edit a record after the
score arrives. Corrections are new records that reference the old one.

| Field | Content |
| --- | --- |
| `submission_message` | Must contain the label and `zip_sha256[:12]`, e.g. `v3 920fcfba647e`. |
| `zip_sha256`, `zip_bytes` | Hash and size of the exact uploaded file. |
| `binding` | `direct` (hash in message) or `inferred` (historical only). |
| `local_certificate` | Path and SHA-256 of the archive verification receipt. |
| `local_score` | Full-precision pinned-metric aggregate. |
| `metric_sha256` | Hash of the metric notebook checked by the drift gate. |
| `kaggle_public_score` | String exactly as displayed. |
| `delta`, `band`, `reconciled` | Difference, the applicable band, and its verdict. |
| `submitted_at_utc`, `scored_at_utc` | Times from the CLI listing. |

`tools/kaggle_receipt.py` has three subcommands.

```bash
uv run python tools/kaggle_receipt.py prepare releases/RELEASE_ID --label v3 --output runs/kaggle/v3
uv run python tools/kaggle_receipt.py record runs/kaggle/v3
uv run python tools/kaggle_receipt.py reconcile runs/kaggle/v3 --ledger docs/evidence/kaggle
```

`prepare` runs the drift gate and `tools/hybrid_preflight.py`, writes the
exact ZIP to upload, and prints the submission message. The user uploads,
for example with
`uv tool run kaggle competitions submit -c google-verifiable-quantum-circuit-compilation -f submission.zip -m "<message>"`.
`record` reads `uv tool run kaggle competitions submissions -c google-verifiable-quantum-circuit-compilation --csv`
and matches the row by message. `reconcile` applies the bands below.
Pin the Kaggle CLI version in the record. The helper never submits.

## Metric drift gate

Before `prepare`, pull the published metric with
`uv tool run kaggle kernels pull metric/google-quantum-ai-metric -p runs/metric-latest -m`.
Compare its SHA-256 with the pinned
`df418aff0d6eff16ec341da20150255abb49b252256d6abfb253ef8d2643ac73`.
A mismatch blocks submission. Diff the notebooks, rerun the affected
local controls under the new version, and record a reconciliation note
before lifting the block. The pinned v10 backend stays the certification
evaluator until that note exists.

## Reconciliation bands

| Archive class | Band | Out-of-band action |
| --- | --- | --- |
| Exact: every component has deterministic cost, or DQI is the pinned reference | `abs(kaggle - local) <= 1e-5` | Stop submissions. Recheck the hash, metric and packaging before the next upload. |
| Failure-priced: DQI cost depends on observed failures | `[min_s(local_s) - 1e-5, max_s(local_s) + 1e-5]` over the registered development salts | Record the implied failure count. Reprice the DQI candidate with `k_max + 2` before the next promotion. |

The public leaderboard uses about half of the test data. A private-split
score can still differ for failure-priced archives. Keep that risk in the
final-selection hedge below.

## DQI salt policy

A public team reported 0 failures in 307,200 local shots and 2 failures on
Kaggle's draw, which cost them about 0.3% in score. Approximate DQI
candidates therefore follow these rules.

1. Register at least five development salts before the first run. Run
   the full 102,400-shot verifier once per salt on the frozen bytes.
2. Report `value_errors`, `phase_errors` and their sum `k` per salt.
   Price promotion decisions with the pinned
   `clopper_pearson_upper_bound` and repetition factor at
   `k_max + 2` failures. At 102,400 shots the factor rises from about
   1.19126 at `k = 0` to about 1.24000 at `k = 14`.
3. Keep the one-use fresh-salt confirmation for the promotion run only.
4. Exact candidates need one development salt plus the confirmation.

## Screen outcomes

Add `budget_limited` beside `go` and `no_go` in `src/qcompile/experiments.py`.

| Outcome | Condition |
| --- | --- |
| `go` | The registered gate passed. |
| `budget_limited` | A registered cap ended the run, and the objective improved by at least 1% relative over the last 25% of evaluations or the optimizer reported non-convergence. |
| `no_go` | A proved bound excludes the gate, or the objective plateaued (less than 0.1% relative improvement over the last 25% of evaluations) while still more than twice the threshold. |

A `budget_limited` lane may be re-registered with a larger budget. It
never counts as a negative result. Re-label the three compressed-shape
records `r9-b129-c40`, `r9-b143-c40` and `r10-b129-c40`. Each ended at
the 20-evaluation cap while still improving, with residuals of about
3.1 Ha against a 19.5 mHa gate. Keep the original files and add
superseding status records.
[Pilot record](../../../docs/evidence/advance-hybrid-20261108/chemistry/r9-b143-c40.json)

## Packaging negative fixtures

Extend `tools/hybrid_preflight.py` with fixtures that must fail. Derive
each boundary from the pinned metric where it defines one. Label local
guards that the metric does not enforce as `local_guard`.

- A qubit or bit id at or above 699,050.
- An NPZ array that is not npy format 1.0, little-endian or float where
  float is required, or an NPZ above 64 MiB.
- A missing, duplicated or non-contiguous `angle_k_*` index.
- `Z_POW` inside an ANGLE or DQI circuit.
- An ANGLE circuit above 128 qubits.
- Register names or widths that differ from the contract (`x`, `S0`–`S69`, `E0`–`E4094`, chemistry selection and word registers).
- A ZIP member path outside the canonical member set.

## Submission cadence and final selection

- Kaggle allows 5 submissions per day and scoring takes about 45 minutes.
  Submit only archives with a local certificate and a passing preflight.
- Upload each new certified archive within 24 hours of its certificate.
  Earlier receipts catch packaging and evaluator drift sooner.
- From 13 January 2027 keep at least two slots per day unused until the
  final selection is made.
- Final selection uses both slots. Slot 1 is the best certified
  archive by local score. Slot 2 is the best certified archive whose
  DQI component is exact, as a hedge against private-split failures.
  If slot 1 is already exact, slot 2 is the next best exact archive.

| Date | Milestone |
| --- | --- |
| 8–9 Nov 2026 | v3 receipt recorded and reconciled |
| 13 Jan 2027 | Entry and team-merger deadline; architecture freeze |
| 13–19 Jan 2027 | Final certifications and receipts only |
| 20 Jan 2027 | Final submission deadline; two selections made |

The 20 November milestone prize and the 4 January Longest Leader prize
require leaderboard positions this project does not hold. Public
notebooks stay out of scope.
