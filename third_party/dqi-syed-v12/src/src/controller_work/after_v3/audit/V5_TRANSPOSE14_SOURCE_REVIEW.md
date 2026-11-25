# V5 transpose14: independent source review

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**Conclusion: no source-level blocker found in the frozen packet.** This review
does not execute its component checker, reconstruct physical inputs, build a
circuit or claim a native result. The full size-11 handoff and 266-case joined
preimage gates remain required before this change can enter a v5 tape.

## Exact reviewed packet

All paths below are relative to `controller_work/after_v3/k24/v5_transpose14/`.

| File | SHA-256 |
|---|---|
| `SOURCE_MANIFEST.json` | `c2a4e114553a3a94f1e136d0beee4adb8e1785545cbec3384ca92b96b4966438` |
| `transpose14_core.py` | `8b5eb93766ac6d9ef638594829ec8f6d27945e84b610c718b4cf9bea73ab039d` |
| `transpose14_window.py` | `1c25f660a58f7907602e60cfc32fbfc51a2775023cc911e33d5d10c2860236b4` |
| `check_transpose14_preimage.py` | `64b8e50eb58f1310c1f79faec0a47c97db42807ffae5a6d5b358574f583e15fb` |
| `check_handoff_m11.py` | `530de18308390713ad79a1a018a7fd77ba9f8395ac4253d92f04cdae77d88250` |
| `profile_supplement.py` | `315bcf5c76b04aece6b294bbbd00ef6610f8e18ef1d920f18173dd66004cb50b` |
| `variant_support.py` | `f0bd00e712d1f73790dd724d749de8541a492f404efde9867a9a3372d1298f0c` |
| `EXISTING_PROFILE_SUPPLEMENT.json` | `58303e050c3caa104bf5538ba76fd159cfb3b054addbfc5a02f343b0d1edd3dc` |
| `SOURCE_DERIVATION.json` | `8ca3ea41c67f14c2ef5fdfe6a683b2b06ab8c1415b4d4bc1cae4c47903f98d00` |

The emitter change is exactly one recursive module-name replacement in the
core and two replacements in the window: its core import and the fixed
transpose-window set `{17,14}`. The existing outer provider still uses that
same core, and both outer and core retain `paired_phase63`. No new arithmetic
primitive, lower-window placement, admitted-domain predicate or phase oracle
is substituted. The source derivation reproduces these literal changes and
the separately listed checker changes; it does not silently compare a new
provider against old bytes.

## Count, phase and witness ownership

At capacity 14, the original shared transpose substitution was 80 T more
expensive per direction than the ordinary frames. The selected retained
predicate tensor removes 88 T and its final predicate handoff removes a
further 11 T per direction. The net change is therefore −19 T per direction,
or **−38 static and expected T** for the pair. This is an unconditional count
change. The extra compact inverse constructions have their actual inverse
masks merged into the next reciprocal witness and repaid by Clifford phase;
there is no additional 27-T inverse phase to charge or discount.

The full checker requires four actual handoffs at the restored source
witnesses: `(n,closing,pay) = (12,false,true), (12,true,false),
(15,false,true), (15,true,false)`. Each handoff is claimed once, allocates no
new quantum wire and leaves no unpaid existing flag/local mask when payment
is required. The provider's original callback multiplicities and source
views are unchanged. Both forward windows and all four transpose calls are
counted rather than inferred from public placement alone.

The proposed pair is 115,043 static T, prefix 57,034 T and Q889. Its exact
fresh-mask expectation is `3933395305086733/34359738368`, or approximately
114,476.87007855662 T. The full and prefix event lists must equal the frozen
v4 preimage lists byte-for-byte as JSON values. Eighteen paired63 calls,
14 park/unpark cycles, two parked phase payments, all 32 local debts and the
single top16 gauge requery remain explicit gates. The count does not claim
a whole-decoder measurement or an official price.

## Fixture completeness and domain scope

The isolated size-11 test invokes the unchanged handoff checker with all
four modes, 256 cases, two prefix/pair builds and three HMR seeds. The full
preimage checker retains every one of the original 256 fixtures, their
arbitrary RHS values, both gauge charts, oracle and three seeds. Those
original fixtures are all mode000 at the newly used 14/13/12 boundary, so
they alone would not qualify the new placement.

The additional ten cases come from exactly five saved physical records at
indices 3205, 3320, 3605, 5894 and 6385, each with two gauge charts. The
supplement requires exact equality with those original records, reconstructs
their padded locator through the unchanged pure reference, and independently
checks the full preimage result through the old preimage reference. The
original input file, reference and reused arbitrary RHS bank are hash-bound.
The new coverage is mode100 twice, mode010 four times and mode001 four times.

Three saved physical inputs have weights 9 or 10. Their six gauge-chart
cases remain explicitly **outside the complete decoder's cutoff15 domain**;
their padded locators satisfy the preimage component's existing domain.
The other four supplement cases are whole-decoder admitted. No sampled
population, input law, failure count or census event is changed by this
component-only use. All five locators satisfy the original constant-gcd,
drop-at-most-two and excluded-window conditions. Adding transpose14 uses
the already excluded simultaneous gap pair 14/12, so it introduces no new
failure class.

The wrapper rejects smoke coverage as a full gate, checks source preservation
before and after, and requires identical new prefix/pair builds and clean
scratch. Prefix phase remains deliberately unclaimed because its legitimate
debts close on the paired return. The pair checks phase as well as all values,
original masks, source words and scratch. Native gates and the eventual
joined v5 gates remain independent obligations.
