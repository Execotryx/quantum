# Fixed v5 integration: source preparation

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**This is a separate source-only candidate. No v5 tape has been built or
tested, and no v5 official gain is claimed.** Frozen v4 files, its receipts,
the original verifier and the frozen population classifier remain unchanged.
Root owns every native, build and official invocation under the shared guard.

## Selected changes and exact source ledger

The proposed composition contains exactly two additions to frozen v4:

1. `first2_retained_norm_adapter` replaces only the three production first-two
   closed inverses by `inverse_retained_norm195`. The generic reverse loop
   has restored the publicly initialized carry to constant one. The adapter
   temporarily clears its low bit, borrows all 24 owned carry bits, restores
   every borrowed bit after each inverse, then restores the constant one.
   The unchanged owner subsequently resets and frees that carry. This is
   not an arbitrary-initial-carry interface.
2. `transpose14_core` and `transpose14_window` add the existing retimed,
   handoff-capable transpose at public capacity 14. The accepted capacity-14
   lower window and its existing exclusion of simultaneous gaps 14/12 stay
   unchanged. This adds two actual transpose calls and two predicate
   handoffs, while preserving the local and reciprocal debt lifecycles.

| Component | Frozen v4 static T | Proposed v5 static T |
|---|---:|---:|
| Extractor, rolling flags, gauge and padded scalar seed | 152,153 | 151,910 |
| Polynomial synthesis | 65,076 | 65,076 |
| Preimage, gauge parking and shared windows | 115,081 | 115,043 |
| Projective finish | 7,856 | 7,856 |
| Shared finish/outer reciprocal seam | −92 | −92 |
| Full scan | 44,275 | 44,275 |
| **Total** | **384,349** | **384,068** |

The retained norm stack saves 243 static T and exactly
`1020002241/4194304` expected T. Transpose14 saves 38 static and expected T.
The combined source saving is **281 static T** and exactly
`1179385793/4194304`, approximately **281.18748497963 expected T**.
The full proposed source expectation is
`13168886125240077/34359738368`, approximately **383265.02909302 T**.
These are source expectations under the existing fresh-mask law, not
official sample means, observed error counts or prices.

The physical maximum remains **Q889**. The public generator has the same
output/log/memory options as v4. It provides no terminal degree, gap profile,
contact set, field alias, cutoff or verifier-salt argument. Public cutoff 15
and all 4,095 physical scan positions are fixed. The separate engineering
builder retains v4's bounded partial-scan option for component work only.

The production key source count is 216,986 T, with unchanged prefix 101,058 T.
The preimage prefix model is 57,034 T. The new source-derived norm-stage
counts are 69 in the key and 119 overall, with historical 72/122 retained
as reference fields. They are not instrumented literal function counts:
the unchanged last-return path already retains its child explicitly. The
exact −243 delta includes the whole replacement; no separate discount is
deducted again from the stage counts.

## Fail-closed evidence boundary

`v5_binding.verify_components` runs before the native-dependent arithmetic
providers are imported. It requires both the immutable v4 provenance chain
and a new completed four-component manifest. The source plan cannot enable
emission. `NATIVE_COMPONENT_GATES.json` must remain absent until root runs
the separate `prepare_component_gates.py` against actual normal, full native
receipts for:

- the isolated retained-norm195 inverse;
- the complete production first-two key, including the preserved physical
  gauge-one fixture and direct observation of the public carry seam;
- the existing transpose handoff at the new low size 11;
- the complete capacity-14 preimage caller, retaining the original fixtures
  and its explicitly labelled additional component-domain cases.

Smoke-only, incomplete, changed-source or stopped results cannot create a
passing manifest. The binding preserves all 112 actual frozen-v4 runtime
source entries and its completed 17-component/163-file manifest. It does
not read the old compiled circuit or reuse old official observations as v5
results. New source inventories name the actual new imports and format;
there is no temporary old-provider rebinding to satisfy preservation checks.

## Event ownership and unchanged wrappers

The retained-norm provider is imported before the existing alias-aware
event hooks are installed. Its three child-mask phases are recorded only
by the existing `scalar_inverse_six` hook. The new key has four such events:
one unchanged last-return event and three new first-two repayments. The
three old retained-child30 and outer54 events are absent. No manual event
duplicates a scalar phase. The full event multiset is asserted, including
18 paired63 calls, 18 final converter inverse phases, 16 converter zero
phases and the unchanged parked-scale and tail events. The transpose14
source model changes only unconditional T counts.

The copied equality, key and physical-panel wrappers retain the original
oracles and checks. New file/module/status names and the new source binding
are explicit. The original 781-key/76-exclusion gate, the full 10,073-case
corpus, the 42 physical fixtures covering weights 15–35 and the preserved
actual physical gauge-one fixture remain future joined gates. Passing the
component manifest alone is not a joined native or whole-decoder result.

After a fixed full tape and reproducible build are qualified, four fresh
original official runs are required to bank a whole-decoder improvement.
Each uses its actual integer failures and returned factor. The 351-billion
goal remains separate from banking a measured T gain. Neither v4's sample
means nor the population upper bound substitutes for a new v5 score.

## Current status

All files here are new. Preparation consists only of source edits, bounded
AST/hash inspection and exact rational ledger arithmetic. The native gate
manifest is intentionally missing. The held source plan has 39 pre-pinned
files, including the exact original key corpus, existing rare physical
fixture, key harness, physical oracle and carry-scale adapter. Report hashes
cannot substitute a different corpus with matching counts.

Independent source reviews are saved outside this directory:

- `blocks/V5_RETAINED_NORM_BINDING_REVIEW.md` covers the selected inverse
  import order, production carry ownership and event ledger.
- `k24/V5_COMPONENT_GATE_SOURCE_REVIEW.md` covers the binding, pure gate
  producer, original fixture identities, exact wrapper copies and full
  266-case preimage coverage.
- `audit/V5_TRANSPOSE14_SOURCE_REVIEW.md` covers the added public window's
  arithmetic, predicate lifetimes, count and component-domain supplement.

Root must complete every full report and normal guard named by
`COMPONENT_GATE_PLAN.json` before invoking the pure producer from the
workspace root:

```bash
/usr/bin/python3.13 -B controller_work/after_v3/integration_v5/prepare_component_gates.py
```

The producer refuses a missing, partial, changed-source, smoke or stopped
gate and refuses to overwrite a manifest. It does not launch any job. Once
the four-gate manifest exists and root explicitly selects this source set,
the fixed public entry can build into new paths:

```bash
/usr/bin/python3.13 -B controller_work/after_v3/integration_v5/gen_dqi.py \
  --output controller_work/after_v3/integration_v5/runs/a/dqi.kmb \
  --log-directory controller_work/after_v3/integration_v5/runs/a/build
```

The generator uses the unchanged shared guard. These commands are provided
for root's queue; neither was executed during source preparation. No newer
matched-prefix or cubic62 provider is included by this source plan. Any
later selection requires a new explicit binding and reviewed gate plan.
