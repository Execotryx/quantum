## Baselines and scope

| Evidence | Qubits | Observed result |
| --- | ---: | --- |
| Banked D4, v8 selection | 897 | 416,454,072,253.15 pooled, four phase and zero value errors |
| Banked D4, later repair campaign | 897 | 414,840,001,725.70 pooled, zero observed errors |
| Full-grid projective repair | 4,081 | 63,747,071,243,053.88 pooled, two value errors and zero phase errors |
| Guarded regular, adjacent and separated probes | 1,011 / 1,240 / 1,503 | Approximately 495,129 / 540,441 / 561,015 executed Toffoli-like gates per shot on their respective fixtures |

The two banked rows use the same circuit SHA-256
`53d8b2edf251e2a0c54c401a97d1396c7ed309e1cbfaab8d54a2c99a11ed6552`
with different draw registrations. Both full-grid value errors were
deliberate rejection at scratch wire 840. A homogeneous control cleared
those inputs and retained a phase residual on historical s2 shot 45440.
The linked compact routes leave unsupported cases. The regular compact
lane's observed gate count already exceeds the ceiling at the 840
syndrome wires alone. The separated zero-slope chart has scalar evidence.

[Banked member](../../../docs/evidence/vendored-dqi/dqi-v8.json) ·
[Repair campaign](../../../docs/d4-cloud-verification-15-11-2026-20-32-51.md) ·
[Measured lanes](../../../docs/d4-measured-lane-no-go-16-11-2026-04-37-47.md) ·
[Separated chart](../../../docs/d4-separated-mixed-tail-16-11-2026-13-23-16.md)

## Candidate intake

Public reports establish leads. Intake pins the exact source and circuit,
and eligibility comes from locally reproduced evidence. Record each
lead's upstream author, revision and file path, full license scope,
complete dependency lineage, published output hash if available and
source archive hash. Confirm that generated code, helper modules and
composed circuit segments are covered. Apply the existing vendoring
policy and exclusions.

| Lead | Evidence and first action |
| --- | --- |
| Syed Asad Ali v12, 889 qubits | **First intake.** Astra inspected the published source archive and confirmed that its build instructions pin the verifier and Kickmix hashes used by this project. Kaggle lists the source package and version notes claim a cost of 360.73 billion, 13.04% below the historical banked control. The project's rebuild, regression and pooled price are pending. [Pinned dataset](https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio/versions/12) |
| Asterios Panoras readout-window recipe and its Atakan Aldemir h5 parent | Circuit Atlas v4 lists recipe `245527f68413` with a claimed 48-gate saving. Resolve the exact h5 input and the matching generator and verify full file hashes and terms. [Circuit Atlas v4](https://www.kaggle.com/datasets/asteriospanoras/qcc-circuit-atlas/versions/4) |
| busyaprime exact product caching, 892 qubits | Resolve script version 363022592 and audit the complete generator chain, especially any section derived from a prior circuit. Measure the same readout and reversal stages with and without the rewrite if both can be rebuilt. [Notebook](https://www.kaggle.com/code/busyaprime/lb-22-86841-22x-cheaper-than-google-s-circuits/notebook?scriptVersionId=363022592) |
| hengck23 iteration 014, 889 qubits | The public comparison reports cost about 410.27 billion on its own draw and one value failure. The author described binary module composition and generator recovery as subsequent work. Confirm a reproducible licensed generator before intake. The public design also motivates an independent projective recurrence audit. [Author discussion](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753607) · [Public comparison](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753923) |

Rank complete source lineage and native correctness before headline
price. Exact duplicates by KMB hash receive a single screen. Preserve
incoming upstream files under `third_party/` with the source manifest and
notices. Keep our adapter in `src/qcompile/vendored/` and apply local
changes there. The existing Q880 is a differential control for eligible
specific kernels. Its historical priced result is materially worse than
banked D4.

### First implementation lane

Use the DQI files from Syed v12. Inspect the source before running its
build script, including its manifest and redistribution scope. Pin the
8,486,126-byte `dqi_source_zip` at SHA-256
`49e2b331d4008afb724985caf1038765b7a910f08838b590bf6e8fb692772763`.
The author build pins a 455,590,024-byte output with SHA-256
`7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9`.
Cross-check both against `SHA256SUMS` and the inspected builder before
creating the admission record. Resolve all imported inputs and recreate
the pinned Python 3.13 / NumPy 2.2.4 environment in isolation. Run the
reviewed `build.sh` using `PY=python3.13` and the pinned engine and
verifier directories. Its entry chain is `gen_dqi.py`, `build_v7.py`
and `v7_pipeline.py` under `controller_work/after_v3/integration_v7/`.
Use a fresh destination per build and record runtime and memory.
Use the inspected 889-qubit / 384,003-static-gate build assertions as
reproduction checks. The v13/v14 public Q890 artifacts are a separate
lead pending exact corresponding generator and license proof.

The v12 architecture uses projective extraction and rolling
continuants, shared norm and window-transpose work, and an adaptive
readout gauge selected from the classical mask. Audit the fixed
69 zero-mask points and selection among 64 classical gauge candidates.
Reproduce gauge open, phase compensation, the one projected scan and
gauge close. Reconcile 4,026 emitted point tests with phase coverage
over all 4,095 points by proving the omitted contributions cancel.
Audit the source's `j_min=15` admission policy at its boundary.
Trace the first differing boundary on any captured or generated
failure and distinguish a source eligibility cutoff from a native
scratch or phase failure. Classical selection may use the verifier's
classical `E` inputs and correctly repaid measurement bits. Inspect
its data dependencies for hidden input labels, draw identity, or
an unaccounted dependence on live syndrome.

If v12 fails the pole or termination fixtures, first test whether an
exact projective step can replace the restricted step within its
existing register layout. Build scalar oracles on either side of the
offending boundary, compare projective pairs up to common nonzero
scale, then test the linked native correction and its inverse with
all other stages held fixed. If a fallback needs extra storage,
count that storage in the declared width and price the guard's
executed cost on regular shots. End the repair trial when the gate
fails or no exact bounded substitution is supported by the trace.

If v12 clears the regressions, a small optional optimization may target
the confirmed readout boundary. Apply the public readout recipe only
when its gate window, live interface and lineage match. Otherwise
examine shared products between readout and inverse readout. Enumerate
products using actual operand
identities and live intervals, including the cases where the readout
gauge or degree differs. Reuse a product only when both operands are
preserved and the same value can be uncomputed at its last use.
Compare an explicit compute/use/uncompute schedule with measured
cleanup including the corresponding cancellation phase. Compute the
paired change in `Q² × T` using the complete circuit. At a constant
executed count, one added qubit at 889 raises the base cost by roughly
0.225%, so quantify this effect before committing a cache register.
If v12 already shares the identified products, preserve it as the
baseline and screen only a demonstrably cheaper eligible boundary.

## Correctness and linked implementation

1. Reproduce the four original phase errors and passing neighbors from
   the original 1,024 captured shots. Reuse the exact s6 and s7 residual
   batches from `matched-residual.json` and explicitly include the
   homogeneous s2 residual. Deduplicate by batch
   identity and test each unique batch once per role and seed. Preserve
   the archive and include a separate receipt for every replay.
2. Extend the fixture set with exact weight 0, 31–35, leading chart
   collapse including the two known incoming poles, adjacent and
   separated mixed poles including zero-slope and the denser witness,
   and rank or degree termination. Generate sparse errors and masks,
   derive their syndromes from the pinned benchmark and derive signs
   independently from the sparse error supports. Check that used
   fixtures actually hit their named scalar chart. Include zero masks,
   alternative masks and multiple fixed simulator seeds. No historical
   shot identity may select a specialized path inside the decoder.
3. Reuse the capture checks in `tools/dqi_matched_batches.py`. Keep the
   legacy full-grid registration check intact. Generalize only the
   infrastructure needed to compare verified build and replay receipts
   across candidate lineages. Record a mismatch even if it only affects
   a mask that the verifier does not charge separately.
4. For a local readout or cleanup ablation, profile the stages on
   production-equivalent serialized bytes. Bind the register order,
   live fields, coefficient basis, scale and rank strata at the
   boundary, including zero and pole semantics and functional coverage
   over the 4,095 field points. Verify forward and reverse together. A measured
   erase must account for the measurement-dependent phase and may reuse
   a wire only after its lifetime and cleanup contract are established.
   Preserve input-independent coherent behavior. Test deliberately
   altered phase repayment and stale workspace controls before pricing.

## Economic screening and qualification

The pinned verifier prices `R × Q² × T`. The repository's comparison
uses the maximum per-draw `Q² × T` base with the pooled repetition factor
derived from disjoint errors. For screening use the later historical
banked price `B = 414840001725.7007` and the minimum eight-draw repetition
factor `R_min = 1.1967314991687559`. Recompute both from the pinned
reference receipts. The provisional ceiling is `B / (Q² × R_min)`.

| Declared width | Maximum executed Toffoli-like mean for break-even |
| ---: | ---: |
| 840 | 491,275.76 |
| 888 | 439,600.29 |
| 889 | 438,611.87 |
| 892 | 435,666.53 |
| 897 | 430,823.14 |
| 926 | 404,261.08 |
| 1,011 | 339,142.01 |
| 1,503 | 153,449.66 |

Preregister two representative development panels of 4,096 official-format
shots each with exact matched inputs and simulator seeds for all roles.
Use the larger panel mean for the numerical screen and publish targeted fixture
costs separately to expose expensive paths. Declare the threshold and
margin before running. At 889 qubits the v12 builder's static count
would give a preflight cost of 363.19 billion if the measured mean
equaled that count and the repetition factor were minimal. The
provisional gate allows 54,609 more executed gates per shot than the
builder's static count. Price the actual executed mean and report
the sensitivity to extra observed failures under the pooled rule.
Crossing the threshold on development fixtures
is a resource-screen decision and supplies no statistical bound on
complete verifier draws. For a single restricted repair, charge guard
and uncompute costs on regular shots, and evaluate fallback worst-case
width even if fallback is rare. At a given total width, report the
resulting saving or remaining gap against the ceiling.

Freeze at most one finalist with complete stage and whole-circuit
receipts. Allocate eight fresh salts, keep them disjoint from all
prior and confirmation reservations, and compare 102,400 official
shots per salt and role. Run the first two registered draws per role
before proceeding to the remaining six. Stop a failed finalist when a
draw fails verification. Any early stop records an
incomplete campaign and is ineligible for selection. Equal salts retain
circuit-specific streams.
Use the independently reconstructed identical-input runs for the error
regression comparison. Preserve raw receipts, all identities, disjoint
failure counters, per-draw width and cost, and independent pooled price
recomputation. Price equality or any qualification failure retains
banked D4. Pin granted cloud resources and the job window in the run
registration after profiling runtime and output disk. The previous
full comparison took about 80 minutes; it should inform the budget.

[Official metric and register-format overview](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/)
