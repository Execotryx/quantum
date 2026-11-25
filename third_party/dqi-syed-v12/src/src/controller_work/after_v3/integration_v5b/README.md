# Fixed v5b integration: source preparation

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**This is a new source composition, with native and official qualification
pending.** It preserves frozen v4 and the separate initial v5 source packet.
It does not reuse either candidate's official observations as v5b results.
Root owns all native, build and official execution under the shared guard.

## Selected composition

The selected v5b adds three changes to frozen v4:

1. The production first-two charts use matched 191-T prefixes and 195-T
   returns. Each prefix retains its actual six-bit norm measurement mask;
   the matching return repays it from the reconstructed original child
   norm. The production carry is public one at both seams, so its owner
   temporarily clears it to borrow 24 clean bits and restores it afterward.
   No arbitrary-initial-carry interface is claimed.
2. The existing retimed transpose with predicate handoff is also used at
   public capacity 14. Its four local modes and the existing exclusion of
   simultaneous gap starts 14/12 are unchanged.
3. The paired quotient phase uses the 20-T cubic GF64 inner trace helper,
   reducing the complete main phase from 63 to 62 T. The outer denominator,
   relative numerator and all measurement-mask repayments are unchanged.

The initial v5 selected the closed 195-T returns and transpose14. It remains
preserved as a separate source packet. The additional matched-prefix and
cubic62 choices are explicit only in this v5b tree. The proposed third
public-carry pivot belongs to a later research tree and is not selected here.

| Component | Frozen v4 static T | Proposed v5b static T |
|---|---:|---:|
| Extractor, rolling flags, gauge and padded scalar seed | 152,153 | 151,907 |
| Polynomial synthesis | 65,076 | 65,076 |
| Preimage, gauge parking and shared windows | 115,081 | 115,025 |
| Projective finish | 7,856 | 7,856 |
| Shared finish/outer reciprocal seam | −92 | −92 |
| Full scan | 44,275 | 44,275 |
| **Total** | **384,349** | **384,047** |

The exact saving relative to v4 is **302 static T** and
`2534932345/8388608`, approximately **302.187483906746 expected T**.
The full source expectation is `13168164570771213/34359738368`,
approximately **383244.0290940929 T**. The source expectation uses the
unchanged fresh-mask law; it is not an official sample mean, failure count
or price. Relative to the initial v5 source model, the additional saving is
21 static T and `176160759/8388608` expected T.

The production key model is 216,983 static T, with prefix 101,055 T and
expected paired T `909145061707/4194304`. The preimage model is 115,025
static T, prefix 57,034 T and expectation `3932776829832973/34359738368`.
The source-derived norm-stage counts are 66 in the key and 116 overall;
historical 72/122 are retained as reference fields. These are not literal
instrumented function counts. The exact replacement deltas already include
the changed inverse stages; no discount is inferred again from those counts.

## Width and event ownership

The proposed complete circuit remains **Q889**. The matched first-two
provider borrows the same owned 24-bit carry bank, restores every bit, and
retains 18 classical prefix-mask bits across the main computation. Its
existing scalar phase hook records four six-bit events in the complete key:
three fresh return cleanups and one unchanged last-return event. Repaying
the three saved prefix masks is Clifford work and adds no duplicate event.

The new quotient62 phase requires **22 helpers**, compared with 18 for the
old quotient63 phase. Its current caller already has the necessary space,
so this does not change Q889. This fact does **not** establish compatibility
with a future width-reduced caller. Any such merge must check the actual
22-helper lifetime alongside its retained reciprocal and gauge storage.
See `WIDTH_COMPATIBILITY.md`.

The paired phase records exactly 18 occurrences of each event
`paired_dual62_exclusive_overlap` (27 T, zero mask bits),
`paired_dual62_rhs_zero` (35 T, 24 bits), and
`paired_dual62_all_masks_zero` (27 T, 36 bits). These replace the corresponding
paired63 family; they are not added on top of it. The 18-call expected gain
is `18*(1-2^-24)`, not exactly 18. The full event Counter rejects the old
paired converter, rare27 and paired63 event families.

## Nine required full component gates

`v5b_binding.verify_components` runs before native-dependent providers are
loaded. It preserves the 112-file actual frozen-v4 inventory, the immutable
17-component/163-file v4 manifest, and the complete 17-file initial-v5 source
packet and its 39-pin plan. A new source plan cannot enable emission.

The new producer requires all nine full native receipts and their normal
guards, including the intermediate gates that led to the selected providers:

| Required gate | Full coverage or purpose |
|---|---|
| Original retained-norm195 inverse | 20,480 cases, three panels, three seeds, two builds |
| Original production first-two retained-norm key | 782 key cases, exact original corpus and existing physical gauge-one input |
| Transpose handoff at low size 11 | All four local modes, prefix and paired scopes |
| Transpose14 with paired63 | 256 original preimage cases plus 10 fixed profile supplements |
| Matched norm-debt inverse | 20,480 cases; open-prefix and closed-pair scopes kept distinct |
| Matched production first-two key | The same 782 cases, both actual public carry seams and all three saved debts |
| Cubic20 trace quotient | All 64×64 field pairs, three seeds, two builds |
| Full quotient62 phase | Six tensor/reference/candidate panels, 20,480 cases |
| Quotient62 plus transpose14 caller | All 266 preimage cases, exact events, 18 paired calls and four handoffs |

The 10 fixed profile supplements are the same five previously saved padded
locators in both gauge charts. Six are below whole-decoder cutoff 15 but
satisfy the preimage interface; four are fully admitted whole-decoder cases.
Their existing labels and exact saved-input identities are retained. No
new sampling, favorable selection or population change is involved.

The initial source plan has 78 pinned source/evidence files, including exact
fixture, harness, oracle and carry-scale hashes. The producer checks the
complete required status, dimensions, phase/value/restoration arrays,
source identities, counts, seeds, guard command and contiguous coverage.
Smoke-only, stopped, incomplete or changed-source reports cannot create the
passing manifest. Its output is exclusively created and never overwrites a
previous native manifest.

## Later whole-candidate workflow

Component qualification is followed by a new full build, a fresh relocated
rebuild with exact circuit and source identity, an unchanged source census,
and the full original joined gates. Those gates retain the 781-key corpus
with 76 exclusions, all 10,073 original physical cases, all 42 physical
fixtures covering weights 15–35, and the existing actual physical gauge-one
fixture. The copied key wrapper changes the expected prefix count by exactly
three T; its oracle, value, phase, mask, scratch and carry checks remain intact.

Only then may root run four fresh original official salts. Each result must
use its actual integer failures, returned factor and measured T count.
Every observed positive-error salt requires exact original-draw attribution
with no new draws. A measured T gain can be banked separately from the
351-billion price goal. An individual salt's price may increase if its
actual failure count changes, even while the circuit uses fewer T gates.

Root's pure manifest command, after every planned full report is complete:

```bash
/usr/bin/python3.13 -B controller_work/after_v3/integration_v5b/prepare_component_gates.py
```

The command only reads evidence and writes the new component manifest; it
launches no computation. After explicit selection and a passing manifest,
the unchanged fixed public argument surface supports a new build:

```bash
/usr/bin/python3.13 -B controller_work/after_v3/integration_v5b/gen_dqi.py \
  --output controller_work/after_v3/integration_v5b/runs/a/dqi.kmb \
  --log-directory controller_work/after_v3/integration_v5b/runs/a/build
```

Neither command was run during this source preparation. Public cutoff 15
and all 4,095 scan positions are fixed; no profile, terminal degree, field
alias or verifier-salt argument is exposed.

The source proof is in `DOMAIN_TRANSFER_ARGUMENT.md`; the machine-readable
model is in `SOURCE_MODEL_LEDGER.json`. Independent source reviews are
kept outside this directory. All native, whole-candidate and official
claims require their own actual receipts.
