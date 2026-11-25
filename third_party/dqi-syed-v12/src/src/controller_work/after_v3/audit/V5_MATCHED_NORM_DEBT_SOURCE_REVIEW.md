# Matched first-two norm debt: independent source review

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**No source-level blocker found.** This is a separate, unselected proposal
relative to the initial v5 195-T-return integration. Its own full isolated
and production-key native gates are still required. This review performed
source reading, SHA-256 checks and AST parsing only; it did not import the
candidate, draw physical inputs, build or simulate a circuit.

## Reviewed source identities

Paths are under `controller_work/after_v3/blocks/v5/`.

| File | SHA-256 |
|---|---|
| `inverse_retained_norm_deferred.py` | `8cb8eaee9312acc81a3048072ec3ddf721399ba8ccdd7eac94002f9d4ec2da46` |
| `first2_retained_norm_deferred_adapter.py` | `095fdf281dd9e959c7980e517eb3cd7ab677d10fdd62c7a305600fb3c530c118` |
| `check_inverse_retained_norm_deferred.py` | `df6722a6c90671f91eadc9f2b6ace79b9154eb71a193589e0c74f6f53fecedd1` |
| `check_first2_retained_norm_deferred_adapter.py` | `10b879908015940dec875c2adb20b9aa8d9956b7b3c92243bdfe47a9f2df6039` |

## Exact deferred witness

Let `N(S)` be the quadratic norm from the 24-bit production field to its
12-bit subfield, and let `h(S)` be the quadratic norm of `N(S)` into the
six-bit subfield, with the same deterministic basis maps used by the source.
The prefix HMR measures exactly the six tower coordinates of `h(S)` and
returns that actual classical mask. All other masks created by this inverse
are repaid before return. The bank is reset, and the only outstanding phase
is the declared scalar product of that mask with `tower(h(S))`.

The matching return receives `inv0(S)`. Norm commutes with inversion,
including the zero convention, so its retained child reciprocal is

`inv0(h(inv0(S))) = h(S)`.

The new return transforms this existing reciprocal into the exact six-bit
tower basis, applies CZ using the saved prefix mask, restores its polynomial
basis and frees that mask. This payment occurs immediately after the
source-preserving child inversion and before the reciprocal is used or
erased. It therefore has the correct value, basis and lifetime. No extra
field register or nonlinear phase is needed. At `S=0`, both sides of the
identity are zero and the same circuit remains valid.

The `PrefixRecord` binds the builder identity, exact source-wire tuple,
extension parameter and still-open six-bit mask. The return rejects a closed
record or a different source/builder/extension before emitting gates. The
quantum-value contract that the matching source contains `inv0(S)` is stated
explicitly; Python metadata does not pretend to certify that value.

## Production carry and restoration

The three special prefix inversions precede generic index2 and never use
the production carry as data. It is initialized publicly to one. The new
prefix toggles its low bit once, uses the resulting owned 24-bit zero bank
for all three inverse calls, then restores one before the first generic
query. The unchanged rolling tail flag remains separate and initially zero.

The generic return restores the same public carry before the three matching
inverses. The adapter toggles it to zero, closes the three debts in the exact
reverse order of their associated values and public transformations, and
restores one before returning to its original owner. The outer owner retains
its original reset/free responsibility. The source never claims support for
an arbitrary initial carry. Both the prefix and return bank lifetimes use
24 already-owned bits and at most 24 additional helpers, maintaining Q889
on the production layout.

The inverse's source-half masks, original-norm mask and final child mask
still have the same explicit repayment and erasure order as the 195-T
primitive. The fresh return child mask is paid by the original scalar phase
helper; it is distinct from the earlier prefix mask paid by CZ. There are
three retained classical six-bit masks across the main computation and no
extra retained quantum word.

## Exact count and expectation

The new prefix costs 191 T and intentionally leaves one phase debt. The
matching return costs 195 T with the existing conditional four-T scalar
cleanup. The pair therefore executes

`382 + 4 * [fresh return six-bit mask is nonzero]`,

with static count 386 and expectation `386 - 4/64`. The original selected
195-T-return variant used the unchanged 192-T prefix, so this proposal saves
**one unconditional T per pair, three static and expected T overall**.
It does not save a further `4/64` per pair: that same return event remains.

Relative to frozen v4, the source model is 246 static T and
`246 + 12/64 - 252/2^24` expected T saved. The production key becomes
216,983 static T and its prefix becomes 101,055 T. The six event families
and occurrence counts of the already-reviewed 195-T production adapter
remain unchanged, including four total scalar-six inverse-phase events.
Those counts must be established by the actual complete gate before use.

## Checker scope

The isolated checker retains the independent polynomial-field inverse and
phase oracle, all five source modes, zero source, dirty bystanders, nonlinear
probes, three HMR seeds and two builds. It copies actual HMR masks into
classical observation bits without modifying outcomes. Exact T checks
discount only the return mask; the open prefix is correctly value-only.
Nine pre-emission contract rejection cases cover the bank and record ABI.

The production checker preserves the full 781 original key-domain cases,
the original 76 exclusions and the existing physical gauge-one case. It
uses the unchanged physical oracle and carry-scale adapter. Four distinct
tapes expose the prefix, complete pair and both carry boundaries. Both
carry seams check constant one; the new prefix seam also checks the untouched
zero tail flag. The full pair checks all values, masks, scratch and phase
through the old independent harness. All four tape kinds must reproduce
byte-for-byte across builds, with the three unchanged HMR seeds. No official
failure rate or whole-decoder score is inferred from those component gates.

Selection into a full candidate remains a separate explicit action after
the proposed native gates pass. The initial v5 source plan is unchanged by
this review.
