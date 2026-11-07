# Next hybrid implementation, 7 November 2026

The code is on `codex/invsqrt-chemistry`. The four OpenSpec changes separate
structural work, measured development, and promotion. No new benchmark,
circuit emission, simulation, or verifier result was produced in this pass.

## Verification

Set `verification_profile` to `candidate-v1` in the candidate configuration.
Registration derives the full shot counts from the pinned benchmark rules
and the chemistry NPZ, then includes those counts in the candidate identity.
The metric worker maps its actual `verified_shots` separately. A full
candidate run requires matching counts in the worker summary and the raw
verifier records.

The current historical control uses the existing contract and coverage
mapping. The versioned profile uses metric v10 `read_circuit`,
`read_npz` and `generate_standard_submission`. The SHA-256 is
`df418aff0d6eff16ec341da20150255abb49b252256d6abfb253ef8d2643ac73`.
The verifier tree pins in `vendor/backend.json` bind
`ProblemSpecInvSqrt.for_n_p` and its 64 repeats,
`ProblemSpecDQI.benchmark_instance` and its 400 batches of 256, and
`dfthcsos.verify.SubmissionInputs.num_vectors` with
`scoreinfra.circuits.SHOTS_PER_ADDRESS`. The chemistry expectation is
`(76 + R * B) * 64`. Exact NPZ payload length and canonical ZIP members are
also checked by the local structural guard.

Register a `release_parent` with the trusted parent `candidate_id`,
`zip_sha256`, `certificate_sha256` and `backend_hash`. Mark immutable
successor inputs as `retained_parent` or reuse the existing reference
provenance when appropriate. A changed component needs a fresh full
confirmation. A retained component is compared by the full member set
and SHA-256 values. If the retained DQI draws or cost differ, the release
evidence needs `matched_parent_verification` with the replay path and
SHA-256. Replay the parent at full strength with the exact successor
archive seed policy. Historical and matched comparisons remain separate.

Run `tools/hybrid_preflight.py ARCHIVE BACKEND OUTPUT` later to check
the pinned readers and register structure without simulation.

## Optimization lanes

- Inverse square root uses `tools/invsqrt_direct.py screen OUTPUT --protocol 2`.
  It rebuilds the reference, Newton and current direct controls. The fit uses
  a 129-point dyadic mesh per interval, 64-digit Decimal exchanges, nearest-even
  coefficient rounding, and the existing exact Horner model. Dense-grid
  fitting is followed by the full-domain model and native checks when run.
- Chemistry uses `tools/chem_refit.py rank`, `fit`, `quantize` and `build`.
  The pilot varies two registered scale coordinates while preserving the
  decoded two-body word table. It regenerates one-body words against the
  fixed official shifts and keeps only eligible improving checkpoints.
  The rank command reports a structural bound before ANGLE Toffolis and
  numerical score factors. The generic XOR loader returns zero for invalid
  selection addresses and enforces the 128-qubit physical cap.
- DQI uses `tools/dqi_prototype.py` for separate multiply, inverse,
  runtime-mask phase, EEA and BM slices. The locator slices take the
  ratio, shift and branch as inputs. A BM degree increase uses a
  zero-initialized saved row to retain the displaced backup. The paired
  `tools/dqi_development.py` runner preserves identical draws and distinct
  scouting, prospective and matched replay roles, with a shared salt
  reservation and an external process-tree sampler.

## Remaining gates

The new paths still require fixture, mutation and native verification runs.
Choosing and building a full DQI decoder depends on measured update/undo
evidence. Changed-shape continuous chemistry fitting and the advanced
inverse-square-root arithmetic and unlookup variants remain follow-on work
behind their respective numerical and reversibility gates.
