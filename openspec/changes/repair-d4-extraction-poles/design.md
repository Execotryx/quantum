## Source audit

The active decoder binds the streamed converter and `replay_erase.extraction`
in [stream/decode.py](../../../third_party/dqi-d4/src/exp/r-main/stream/decode.py).
Forward extraction delegates to the reference. The decoder applies mask
projection and the initial linear map before extraction, then synthesizes
`A, B` before conversion. Its geometry is 17 doubled quadratic nodes and one
trailing zero node. Use it when reconstructing the rational function from the
syndrome. The standalone confluent model uses different nodes.

In [final_decoder/decode.py](../../../third_party/dqi-d4/src/playbook/kit/decoder/final_decoder/decode.py),
`external_extraction` uses ordinary jets for groups 0–7 and homogeneous
chains for groups 8–16. An ordinary jet's safe completion maps `(0,v)` to
`(0,v)`. The homogeneous chain carries a denominator through intermediate
zeros. It normalizes the output and retains its pole bit for reverse. Every
external group then calls the local `inverse24_forward190` on the second word.
`synthesize` receives the trailing chart's pole bit. It does not receive the
external chains' pole and gauge tokens. This makes routing a cohort through
the homogeneous recurrence a direct test for intermediate losses. A genuine
local pole also requires checking the output representation and synthesis.

## Freeze the native diagnosis

Pin the full banked circuit SHA-256
`53d8b2edf251e2a0c54c401a97d1396c7ed309e1cbfaab8d54a2c99a11ed6552`, source
manifest, official backend, and the archived request and captures under
[`docs/evidence/dqi-phase-replay-20261115/`](../../../docs/evidence/dqi-phase-replay-20261115/).
Verify the original batch seeds and reconstruct their inputs with the official
sampler. Snapshot the 70 words after forward extraction and after synthesis by
intercepting the emitter calls without changing the emitted instructions.
Require the instrumented full rebuild to hash to banked D4. Replay the four
original 256-shot batches, and inspect the four failures and four passing controls.

Build an independent rational oracle using the D4 node polynomial and BM/Forney
support. Construct the rational function from roots `alpha^j` and residues
`e_j * alpha^j * P(alpha^j)`. For each node track denominator zero, residual
degree, and exact termination. Freeze the oracle output and the scalar predictions
below separately from native output. Indices are zero-based. Extension words
use `low | (high << 12)`.

| Salt and shot | Predicted singularity | Predicted check |
| --- | --- | --- |
| s2 / 45440 | Genuine local pole at group 6, head 13. Residual degree 18. | Zero input to the local inverse before any synthesis. |
| s6 / 13238 | Ordinary jet at group 6, source head 8, input `(0,3275030)`. | Group head 12 is `2080877`; rational reference `15349215`. |
| s6 / 74119 | Ordinary jet at group 7, source head 11, input `(0,16547885)`. | Group head 14 is `10349127`; rational reference `15086811`. |
| s7 / 46728 | Ordinary jet at group 6, source head 4, input `(0,8361373)`. | Group head 12 is `14765173`; rational reference `11665478`. |

Use a targeted pre-jet or pre-inverse snapshot only where necessary to locate
the first mismatch. Separate the syndrome's legitimate rational termination
from a nonzero residual whose denominator vanishes at a selected node. If
native observations contradict the scalar model, reconcile basis and gauge,
verify the probe against the passing controls, and revise the diagnosis before
changing the emitter.

## Repair and measurements

1. **Intermediate poles.** In an adapter over the admitted source, route
   groups 6 and 7 through the existing homogeneous chain as the first ablation.
   Compare post-extraction words, synthesized support, phase, and cleanup on all
   fixed fixtures. Measure native width, peak scratch and Toffoli cost. Apply
   the repair to every ordinary group whose recurrence can reach a nonterminal
   pole. Prove any group left on the affine route cannot reach that case, and
   exercise representative poles outside groups 6 and 7 where reachable.
2. **Local poles.** If the local-inverse case persists, derive a reversible
   projective update for the repeated node. In the pole chart preserve the
   numerator, denominator, and first derivative information across the two
   heads. Derive the homogeneous two-head recurrence and inverse against the
   rational oracle before emission. Carry the minimum chart information needed
   through the existing external history to synthesis and its inverse. Emit
   an equivalent finite update on regular inputs, a valid rational continuation
   on genuine poles, and the existing terminating representation when the
   residual is identically zero. Document the coordinate and inverse identities
   at each boundary. If the shared head layout cannot express a pole, adapt
   extraction and synthesis together, including the trailing chart input.

   For a finite first head `h`, write `q = X² + X + kappa`. A genuine
   second-head pole has nonzero `N + h D = q² R`. Use the continuation
   `(D, R)` and the paired transfer with rows `(h, q²)` and `(1, 0)`.
   Its determinant is `q²` in characteristic two, as for two regular
   steps. The continuation reverses by reconstructing `N = h D + q² R`.
   This identity alone does not specify the reversible schedule or the
   chart representation in the live syndrome bank.

   At a distinct evaluation node, store `L = D² (N/D)'`. The paired
   continuation maps `(N,D,L)` to
   `(q² D, N + h D, q²(L + h' D²))`. The inverse divides only by the
   nonzero constant `q²` at that node. The standalone native primitive
   implements and tests this transfer. For circuit integration, retain
   the pole chart coherently until it is uncomputed. Forward and reverse
   cannot select the transfer by measuring the syndrome-dependent flag.
   Establish the live bank layout and the synthesis width bound before
   accepting a schedule.

   Let `S = N + h0*D`, `Q = q²` and `J = Q*(L + h0'*D²)`
   at a distinct evaluation node. A regular pair gives
   `(q*S, q*D + h1*S, J + (h1 + q*h1')*S²)`.
   Recover `S` by dividing the first coordinate by `q`, then reverse
   the second coordinate to recover `D`. Use those recovered words
   to undo the derivative update and the first head. A pole pair uses
   `(Q*D, S, J)` and reverses with the analogous constant division.
   Neither transfer divides by a live denominator. The paired
   normalization scales the rational coordinates by the chosen gauge
   and the derivative numerator by its square. The reverse
   recomputes both measured denominator gauges and repays their phase.

   For the all-regular tail, the 34 inverse steps produce two high
   constraints on a degree-`(2,1)` tail. Compute only the top two
   coefficients using `t = 1/X`, with the numerator offset one degree
   above the denominator. Combine the equations at original numerator
   degrees 35 and 36 with the projective derivative equation. For mixed
   charts, the current emitter tries the one-sided linear tail and checks
   the answer from the original moments.

   The full-grid prototype reserves 54 coefficients per bank before
   validation. Starting with degrees at most `(2,1)`, each regular
   inverse pair grows the weighted bound by two and each pole pair by at
   most three. After 17 pairs the numerator degree is at most 53.
   Checking degree bounds after reconstruction cannot rely on truncation
   to the scan width. The validator binds the original Laurent moments
   `S`, the node polynomial `P`, and the polynomial part `Q` of
   `P*S`. Require `N + Q*D = 0 mod P` and nonzero `D` with the full
   degree bounds. The congruence fixes the rational function because any
   difference between valid pairs has degree at most 69 and is divisible
   by `P` of degree 70. The scanner records repeated base-field roots
   separately, since the first derivative cannot recover those residues.
   Both predicates stay visible to the official verifier. The native
   certification and full-strength comparison are linked in the checklist.
3. **Reversible closure.** Test forward with inverse, and forward with phase
   then inverse. Check restoration of syndrome, masks and all workspace, with
   both measurement outcomes on each modified erasure path. Keep regular,
   terminated, intermediate-pole and local-pole fixtures separate. Include
   alternate mask parities so a wrong decoded support cannot pass just because
   two phases coincide. Include negative controls that force the legacy
   clipping on each of the two pole branches and demonstrate detected phase or
   value disagreement. Any unsupported chart must remain visible to the
   verifier as a failure.
4. **Whole decoder.** Regenerate the candidate twice with pinned inputs and
   compare the serialized hashes. Run both original and repaired circuits on
   the same captured batches, with the original explicit input and simulator
   seeds. Ordinary verifier salts derive their inputs from the circuit hash.
   A reused salt alone therefore does not compare the same shots. Require all
   four known disagreements to clear and the four controls to stay clean.
   Compare all shots in the four batches and retain any new failures.

## Full cloud campaign

Use the existing VM with a three-hour automatic stop limit, subject to the
observed runtime of the fixture pass and the full verifier. Run serially to
reuse the measured memory budget. Before starting, check disk headroom for
the two builds and verifier temporaries. Preserve independently hashed
terminal receipts and resume only from verified completed roles. Stop the VM
after collecting results.

Freeze the candidate hash, backend inventory, batch fixture hashes, and eight
new pricing salts before full simulation. Run 102,400 official shots per salt
for each of the candidate and banked D4. The common salts control scheduling
while each circuit hash defines its own input stream. Treat this as an
independent full-coverage comparison. Record value and phase failures
separately, declared width, static and mean Toffolis, and pooled price via the
existing DQI screen formula. Report whether the candidate retains the official
PASS condition at each salt, whether it incurs any new failures in the fixed
batches, and the resulting cost and width trade-off. Preserve the banked decoder
and report a negative result if the repaired candidate fails these gates.
