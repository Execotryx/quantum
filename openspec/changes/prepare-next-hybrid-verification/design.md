## Inputs and authority

The working checkout is `codex/invsqrt-chemistry`. The checked local and
published file tree is `454fa9a9011091cffc155a7191b7f49a547d9c00`, represented
by GitHub commit `fafae3e11be66b45ddb33d2547b1e7a7cbbdfcb0`. Preserve the
original source revisions and hashes in all receipts. An implementation
campaign pins its own clean source commit and frozen `uv.lock`.

Use the [paired comparison](../../../docs/evidence/invsqrt-direct-hybrid-20261107/comparison.json)
and [certified successor](../../../docs/evidence/invsqrt-direct-hybrid-20261107/certificate.json)
as the control for every lane. The ZIP SHA-256 is
`2500a815dd16a9b04185fa8f1c44b6c96e33d38a4d5d397d2bad3b7ab61d9fac`.
Resolve actual artifact locations by hash. Do not rely on the path from the
attached report or on absolute paths from someone else's clone.

| Benchmark | Certified cost | Coverage and context |
| --- | ---: | --- |
| Inverse square root | 1,008,498.1176395753 | 200,540,928 trajectories, 199 qubits, 4,812 Toffoli-like gates, 27.2863% worst phase tolerance used |
| DQI | 24,439,466,510,149.91 | 102,400 trajectories, 1,893 qubits, 5,725,109.06765625 mean Toffoli-like gates, zero observed failures in the paired run |
| Chemistry | 3,247,752,448.668952 | 254,464 trajectories for this shape, nine banked ANGLE circuits and the matching reference NPZ |

The attached investigation is a research input identified by SHA-256
`c3d39e7ee3d4bc0170e5ab5aa2b89ec77075c2af271f96c10e715cd0a8b318ff`.
Use `contracts/contract.json`, the pinned metric notebook v10 and the
inventoried native verifier sources for actual behavior. Keep contest
positions, public component receipts and performance projections separate
from locally verified results. For example, the report's leading score
29.30100 and public portfolio scores are snapshots or third-party
observations. A projected geometric mean of 14.7 from component ratios
10, 40 and 8 is arithmetic, not a schedule or delivery commitment.

## Execution order

| Lane | Start and first deliverable | Dependency before promotion |
| --- | --- | --- |
| Shared verification | Start now. Freeze the control and add independent expectations and receipts. | All lanes use this path for promotion and archive verification. |
| DQI | Highest research priority. Derive a reversible register schedule and a runtime-mask phase proof, then test the first small-field window. | Scoped DQI counters and one-use confirmation. The research lane can start before those are implemented. |
| Chemistry | In parallel. Replay the known factorization/word control and build a classical serialized shape/precision screen. | Dynamic chemistry expectations before changed-shape release. |
| Inverse square root | In parallel. Fit and exhaustively scan a bounded quadratic versus the frozen cubic. | Retained-component lineage and deterministic archive verification. |

Use separate campaign directories and isolated build inputs. Register each
lane's budgets, deterministic job ordering, inputs, stop rules, eligible
candidate grid and tie-breaks before prospective results. Allocate compute
after profiling a reference and one prototype, retaining all partial
receipts and failed lanes. Independent numerical work can run in parallel.
Start the full native verifiers serially. Increase concurrency only after
measuring headroom with external process-tree PSS and separately summed RSS.
The prior successor verification stopped during DQI and completed with
extra swap. A smaller KMB file alone cannot establish reduced verifier RAM.
Use bounded wall/CPU/RAM and disk budgets, process identities, archived
diagnostics and inspect an interrupted worker before resuming. Preserve
native Linux/Python 3.13 and frozen dependencies.

## Tier definitions and measurement

1. **Scouting.** Run proofs, synthetic fixtures, precision models, resource
   estimates and retrospective experiments. Label results accordingly and
   never reuse scouting salts or rows as promotion evidence.
2. **Registered development screen.** Replay the control first. Compare
   candidates on matched workloads and pinned backend. DQI can start at
   2,560 shots (ten pinned-size batches) or a registered larger count. Use
   explicit identical cases when doing a paired development comparison.
   At 2,560 shots with zero errors the official repetition multiplier is
   approximately 4.942, versus 1.191 at 102,400 shots. The existing 256-shot
   archive smoke configuration can reject a zero-error DQI run on its
   confidence bound. A small sample never stands in for full acceptance.
   Do not add execution flags to the numerical scorer
   `src/qcompile/reference/scoring.py`. Put the multi-salt runner in a
   campaign tool that uses pinned verifier inputs and saves raw receipts.
3. **Full-strength gate.** Freeze a passing deterministic artifact, then
   run the unmodified full verifier. DQI full comparison uses actual
   executed mean Toffolis and both disjoint error counters under
   `R(epsilon_plus) * Q**2 * T`, with `delta = 2**-128`. Reconcile
   `N`, `k`, `epsilon_plus`, `R`, width, counts and score.
   Additional full-strength development salts must have a fixed list and
   success rule, with every result retained. Do not select a favorable salt.
4. **One-use confirmation and archive.** Reserve a separate confirmation
   salt once per frozen changed component. Confirm in an independent run
   and store raw result and exact coverage. Then verify the complete
   fresh extraction of the assembled deterministic ZIP under a distinct
   archive role. Different artifact digests can seed different draws even
   with the same salt. A common archive salt pairs unchanged retained
   components only. For DQI differences across seeds, compare matched
   archive receipts by exact retained digest, counters and cost. Preserve
   the original differing observation.

For one component, the projected multiplier over the incumbent aggregate is
`(incumbent_component_cost / candidate_component_cost) ** (1/3)` if the
other costs stay fixed. Rank against the certified incumbent component.
The scorer's official reference ratios remain the denominator for the
complete reported aggregate. Separate mathematical estimates, measured
component costs and actual complete archive scores.

## Coverage, preflight and lineage changes

- Separate the existing reference coverage map from a candidate coverage
  manifest. Inverse square root stays 200,540,928 and DQI 102,400 at
  full strength. Compute chemistry's `(76 + R*B) * 64` from the selected
  pinned NPZ via the official shape/input contract and compare the result
  independently against the raw verifier's actual count. Never derive
  expected coverage by copying a verifier's observed count.
- Thread the expectation through `component_confirmations.py`,
  `experiments.py`, `cli.py`, `worker.py`, `release.py` and the
  `tools/hybrid_certification.py` helper. Preserve existing baseline and
  certified manifests as historical records. Bind expected count, shape,
  relevant input/member hashes and pinned contract/backend to the new
  candidate's registration. Keep DQI's failure-counter mapping separate
  from inverse-square-root and chemistry fail-fast PASS handling.
- Exercise packaging checks with pinned notebook symbols `read_circuit`,
  `read_npz` and `generate_standard_submission`. The metric v10 actually
  sets max qubit **or classical bit** ID exclusive to `2**30 // 1536`
  (699,050), and the declared total NPZ array payload cap to `2**26`
  bytes. Use NPY 1.0 and the official dtype per key, including integer
  `tree_edges`. Validate named registers, supported instructions,
  per-task register caps, contiguous ANGLE numbering and strict ZIP layout.
  Test boundary IDs and NPZ sizes and reject extra or conflicting encodings.
  Keep the official parser as the acceptance authority. Record source hashes
  and symbols for any newly reconciled or changed fields.
- Generalize the current narrow retained-chemistry path only enough to
  support actual new combinations. Distinguish official reference
  members, newly generated components and retained previously certified
  components. A retained component binds the full manifest and parent
  certificate, scope, backend and unused-for-tuning receipt. A changed
  chemistry NPZ invalidates its old confirmation, even with identical ANGLE
  bytes. A newly generated DQI circuit requires its own raw scoped receipt.
  Keep original terminal history and global salt reservations intact.
- Attach method provenance to campaign/candidate manifests, with source,
  version, hashes and attribution. Use independently implemented public
  methods for the proposed lanes. Keep external measurements labeled and
  distinguish a local reproduction from a public claim. Any different
  artifact sourcing policy needs an explicit separate decision.
- Assemble the smallest qualifying changed set first, preserve the current
  certificate as fallback, build twice in fresh directories and hash-compare
  every member and both ZIPs. Require exact full counts, benchmark scopes,
  acceptable measured costs, positive aggregate delta versus the current
  certified incumbent, and retained lineage. Claim external acceptance
  only from a separately authorized and recorded result.

## Sources

- [Sponsor paper, benchmark and verifier model](https://arxiv.org/html/2610.23832v1)
- [Official evaluation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/overview/evaluation)
- [Official metric](https://www.kaggle.com/code/metric/google-quantum-ai-metric)
