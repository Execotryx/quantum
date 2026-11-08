## Control

The reference DQI circuit has SHA-256
`959471d05a26373b4f14ca0cae2d8639ea25f18170d9f6532139aa51ccc04995`: 1,893
declared qubits, mean 5,725,109 and maximum 5,725,461 Toffoli-like gates
per shot, repetition factor 1.19126, cost about 2.4439×10¹³.
`tools/dqi_decoder_screen.py` already rebuilds it through
`ProosAndZalkaDecoder(n, km.GF2Field(12)).build_syndrome_decoding_mbuc`.
[Full-size tower comparison](../../../docs/evidence/advance-hybrid-20261108/dqi/full-shape-tower.json)

## Method

1. Add `StageProfileBuilder`, a proxy like `TowerBuilder`. It delegates
   every call and records three things per call:
   - the decoder stage, from the nearest `dqi_reference_circuit` frame on
     the call stack, mapped to a registered stage name;
   - the gates emitted, by type, from the builder's operation count before
     and after the call;
   - `num_allocated_qubits` after the call.
2. Register the stage map before the run. It names every
   `ProosAndZalkaDecoder` method that emits gates. Unmapped emitting
   frames fail the run. Initial stages:

   | Stage | Expected content |
   | --- | --- |
   | `syndrome_prep` | Any syndrome transformation before the locator solve |
   | `locator_forward` | Synchronized EEA cycles, quotient storage, controlled swaps and shifts |
   | `scan` | Chien evaluation, Forney values and inversions, runtime-mask phase |
   | `locator_reverse` | Reversal of the locator solve |
   | `cleanup` | Any remaining uncomputation and resets |

3. Count Toffoli-like gates by the verifier's definition (`CCX`, `CCZ`,
   `CSWAP` and any other gate it counts as Toffoli-like). Read the
   definition from the pinned verifier.
4. Static counts approximate executed counts closely because conditional
   execution changes the total by at most about 352 gates. Reconcile the
   static total with the verifier's mean on the same circuit, using the
   existing 2,560-shot matched control. Report the residual.
5. Run shapes `(m, n) = (63, 4)`, `(127, 12)` and `(4095, 70)`. The
   full-size run needs the cloud VM (about 8.7 GiB peak process-tree
   PSS was observed for the full-size pair).

Proxy emission must reproduce the reference KMB hash exactly.

## Outputs

- `stage-profile.json`: per stage, Toffoli-like gates, other gates by type,
  peak and entry live width, and share of total.
- Declared width versus traced peak, cross-linked to the tracer in
  `reduce-invsqrt-declared-width`.
- Product-site census: the number of quantum-quantum products, inversions,
  controlled swaps and controlled shifts per stage. This explains the
  5.09% tower result quantitatively.

## Decision record

| Measured locator share (forward plus reverse) | Build order for the new decoder |
| --- | --- |
| At least 60% of Toffolis | Routed BM locator first, then the phase-only scan |
| Scan at least 40% of Toffolis | Phase-only scan first on the existing locator, if a hybrid can clear the gate |
| Neither | Profile the largest unexplained stage before building |

Also record the projected cost of each plan in
`build-routed-bm-dqi-decoder` using the measured stage costs.
