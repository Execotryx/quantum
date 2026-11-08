# Next optimization round: synthesis and OpenSpec changes

Created 08-11-2026-17-31-51 in Asia/Qyzylorda, against `d41ba59` on
`codex/invsqrt-chemistry`. Five changes follow. Each has a fixed number of
steps, fixed budgets and numeric gates. None contains an open-ended search.

## Starting point (v5, local pinned metric 1.6561824298)

| Component | Ratio | Where the cost is |
| --- | ---: | --- |
| Inverse square root | 4.40× | 150 qubits; 2,908 Toffoli-like gates: 766 lookup, 56 unlookup, 1,568 Horner, 56 flags, 160 input shift, 302 output shift |
| DQI | 1.0× | Reference: locator forward + reverse 73.69%, scan 25.23% of 5,725,461 |
| Chemistry | 1.033× | Banked J9 on the reference factorization; best compressed fit 41.57 mHa vs a 19.0 mHa gate |

## What the last round ruled out

These lanes were measured and closed. They are not reopened here.

- invsqrt: gated-operand rows (projected 905,204), signed-digit rows
  (1,194,754), two-octave tables (best passing 516,038), load-as-you-go
  `c2` (599,901), 28/20/13 widths (−0.69% only), and per-term compact
  phasing (≥ 445,859). A coherent phase-gradient register cannot be
  prepared at all: the pinned gate set has no Hadamard, and every
  non-input qubit must start and end at zero.
- DQI: the bounded flip-graph search did not find a rank-15 GF(64)
  multiplier (rank 18 retained after 999,641 flips). A two-bank in-place
  layout needs at least 1,686 qubits. Under the earlier layout (910 static
  history bits and a separate 420-qubit evaluator), a direct-Forney decoder
  projected at most 1.675×.

## Synthesis: what still moves the score

1. **invsqrt lookup recomputes every sibling AND.** `_load_table` and the
   unlookup walk compute one temporary AND per child. Standard unary
   iteration reaches the second child with one CNOT. This repository's
   chemistry loader already does. Halving the lookup is about −13% on the
   component with no change to its arithmetic. → `share-invsqrt-lookup-siblings`
2. **DQI's 2× gap was a layout problem, not an arithmetic one.** The
   contract samples weights 0–35 only, so BM with static degree bounds is
   exact on every input. Three layout changes reach about 1,920 qubits and
   about 1.55 million Toffoli-like gates (about 3.6×) with existing
   primitives: a tagged history of `h` entries instead of 910 static bits,
   a circular template with a classical offset, and the evaluator in place
   over `S1..S35`. → `assemble-routed-bm-direct-forney-decoder`
3. **Chemistry is gated by fitting speed, not feasibility.** L-BFGS halved
   the residual every few thousand evaluations. Alternating projection
   makes exact block moves and removes the rotational freedom in
   `‖H − XᵀX‖`. → `fit-dfthc-alternating-projection`, then
   `promote-compressed-chemistry`, which runs the existing S2, S3 and
   loader commands once.
4. Releases go in one-member steps with receipts. → `sequence-hybrid-releases`

## Aggressive options

| Option | Status | Potential | Why not specified here |
| --- | --- | --- | --- |
| Bounded DQI history (`h` entries, priced failures) | **Specified** | Enables about 3.6× | — (policy change: approximate before exact) |
| Phase-only scan with reciprocal `Ψ = B² + zA²` from a half-degree Euclid on `(E, O)` | Not specified | Scan 930k → about 94k plus the reciprocal; DQI about 6–9× | Gu et al. report 17 elimination blocks, quotients parked in cleared words, `A` and `B` in zeroed syndrome words and 44k Toffolis per direction. The available text does not give the block schedule, so the steps cannot be fixed yet. |
| Adaptive locator cutoffs (degree ≈ r/2) | Not specified | Locator products −20% | Adds failures. Measure after the bounded decoder's failure rate is known. |
| In-place DQI near 900 qubits | Not specified | ×4.4 on DQI | No single-bank construction exists yet. |
| invsqrt architecture near 62 qubits (public frontier) | Not specified | ×4–5 on invsqrt | No public construction detail. A phase gradient is impossible under this gate set. |
| Assembling public Apache-2.0 circuits | Not specified | GM about 24 | Changes the project's independence claim. User decision. |

## Projection (estimates)

| After | invsqrt | DQI | Chemistry | Aggregate |
| --- | ---: | ---: | ---: | ---: |
| v5 (measured) | 4.40× | 1.0× | 1.03× | 1.656 |
| v6 sibling lookup | 5.05× | 1.0× | 1.03× | 1.73 |
| v7 compressed chemistry | 5.05× | 1.0× | 3.3–5.9× | 2.55–3.10 |
| v8 routed DQI | 5.05× | 3.5–3.9× | 3.3–5.9× | 3.9–4.9 |

## Literature used

- Babbush et al., "Encoding electronic spectra in quantum circuits with linear T complexity", Phys. Rev. X 8, 041015 (2018): unary iteration with sibling CNOT transitions.
- Berry, Gidney, Motta, McClean and Babbush, Quantum 3, 208 (2019): measurement-based unlookup.
- Gu, Kemeny, Yelin and Lukin, arXiv:2610.22367: routed BM, history bounds, phase-only scan and half-degree reciprocal (SI I.1).
- Khattar et al., arXiv:2510.10967: reference DQI decoder and GF(2^m) arithmetic.
- Parrish, Hohenstein, Martínez and Sherrill, J. Chem. Phys. 137, 224106 (2012): least-squares tensor hypercontraction. Oumarou et al., Quantum 8, 1371 (2024): regularized compressed double factorization.
- Consensus literature thread for this round: https://consensus.app/search/research-brief-for-a-practitioner-optimizing-rever/TpPGNX9aTMmpnVsNbaAEgw/

## Applying the bundle

Copy `openspec/changes/*` and this file into the repository root, then run
`npx @fission-ai/openspec@1.16.1 validate <change> --strict` for each change.
