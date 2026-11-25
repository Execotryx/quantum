# Complete Q48 gate: 87,842.32264250, native construction pending

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits Opus and Astra.

**The complete construction passes the paper gate at Q48: 1,591 expected
Toffolis, 4 T gates, and 34 rotations give 87,842.32264250.** This is
335.54838839 below native candidate05 and2,144.67735750 below89,987. It is a
fully specified composition awaiting an isolated emitter and native proofs;
it is not an officially qualified circuit.

The authoritative [JSON receipt](Q48_COMPLETE_PAPER_GATE.json) records every
component, all ownership cuts, source hashes and thirteen explicit integration
obligations. Its [read-only checker](q48_gate_audit.py) verifies the pinned
receipts and small exact sums without importing native code or running a
heavy job. The existing candidates remain immutable.

## Complete cost

| Component | Expected Toffolis |
|---|---:|
| Direct pair normalization, complete round trip |97.5|
| Consuming root, including constant-tail specialization |198|
| Divider with triangular initialization and disposable feed carry |587.5|
| Paired consuming product with disposable owned rounding carries |240.5|
| Coefficient rows: two forward passes and one inverse |123|
| Seed preparation and complete phase cleanup |17.5|
| Coefficient R frames |4|
| H3/H4 preparation and reconstruction |7|
| Five-root value decoder |21|
| Actual first loader |61|
| Actual framed second loader |80|
| Shared table-debt/output cleanup |9|
| Compact endpoint including translated route and two swap omissions |145|
| **Total** |**1,591**|

The complete coefficient/seed/product/table/root-decoder lifecycle is563E;
excluding product240.5, its cost is322.5E. No table or reconstruction remains
outside this sum. Four T gates add1E. The same exact candidate04 angles have
charge238.04838838550535, yielding1,830.04838838550535E per shot and the Q48
total above. Original tolerance and the coefficient model are unchanged.
The inherited exact quantized phase margin is124,372,027 units on the2^64
comparison grid. Preserving that phase is a mandatory native proof obligation.

## Actual preparation and inverse ownership

Frozen mathematical certificates and independent128-row replays are in
`frozen/manifest_Q48_v1.json`. The first61-E loader uses26 fixed owners plus22
work owners, including all16 outputs. It preserves the raw address and returns
42 owners. The second80-E loader uses27 fixed owners plus21 work owners,
including four existing input values and all16 outputs. It allocates only
**17 new zero owners**, not21.

Before the second load, move the already priced R frame to its new position.
Its fixed address coordinates are R,a5,a6; mutable input owners are
a0,a1,a2,a4. Every recorded frame remains injective on all128 rows. The
second load returns43 live owners, with those four raw input slots absent.

| Binding cut | Complete live ownership | Wires |
|---|---|---:|
| First loader peak |root12+residual10+flags4+work22|48|
| Second loader peak |rootlow5+R+a5+a6+product15+flags4+work21|48|
| Second loader return |rootlow5+R+a5+a6+product15+flags4+A13+Hlow3|43|
| Initial H3 prepared |preceding43+H3|44|
| Only a6 directly retired |rootlow5+R+a5+product15+flags4+A13+H0..3|43|
| Second coefficient prepared |root7+product15+flags4+D13+H5+snapshot1|45|
| H3/H4 erased |root7+product15+flags4+D13+Hlow3+snapshot1|43|
| Inverse product |root7+word16+flags4+D13+Hlow3+snapshot1|44|
| Seed cleared |root7+residual10+flags4+D13+Hlow3+snapshot1|38|
| Current H3/H4 restored |preceding38+H3+H4|40|
| Initial A restored |root7+residual10+flags4+A13+H5|39|
| All root values restored |root12+residual10+flags4+A13+H5|44|
| Body return |root12+residual10+flags4|26|

Initial H3 uses A10..12,H2,rawa5,rawa6, so it must precede a6 retirement.
Moving the R frame earlier changes only a3; a5/a6 remain available. H4 and
the second snapshot are created after a6 retirement. The later44-owner
inverse-product chart is identical to the one priced in the carry study.
Normalization peaks46, the root peaks41, seed cleanup peaks47, and the
source-expanded arithmetic and compact phase fit48.

## Required phase and owner interfaces

The isolated table adapter must use the exact recorded affine matrices with
offset `1+len(fixed)`:8 for the first load and4 for the second. It returns the
current physical A/H owners and marks `v[5],v[6],v[7],v[9]` absent after the
second load. No stale physical input handle may survive as a logical owner.

The first/second loaders create45/64 HMR generators. All mixed early-input
functions are expressed in the original raw-address row order and go only
to the shared `TableDebts` ledger. They are repaid after the raw address and
initial A/H chart are restored, followed by the full9-E cleanup. The existing
rank128 final chart covers all these functions.

The21-E decoder still reconstructs raw a0,a1,a2,a4,a6. **Only a6 has a direct
per-bit HMR outcome to correct at that point.** The four early inputs receive
no duplicate raw-bit Z; their mixed signs already belong to `TableDebts`.
The decoder API must explicitly distinguish these cases. R is unframed only
after the missing root values have been reconstructed.

The first A6 snapshot is repaid on second A6 before mutation. The second
snapshot stays live through inverse product. First D13 signs wait for the
exactly regenerated second D13, where all13 conditional Z gates are applied.
Both coefficient forward carry transcripts are XOR-merged by position and
consumed by the final row/overflow inverse. H4 is erased before H3 with
immediate quadratic phase fixes, and both are reconstructed for the final
coefficient inverse. Seed17.5 includes every old carry, the conditional fifth
helper and its two-outcome repair, both seed frames, and all data erasures.

The product carries are disposable only in rowsi0..7. Rowi8 isFalse, and
rowi9 aliases the live product control; neither may be freed. All callbacks
use the original carry constructors and exact phase erasers after source
and dirty controls have been restored. Skip the caller's erase only when the
arithmetic routine returns `released_input`. Product240.5 already includes
eight conditional regenerations costing4E. The divider's analogous13 feed
regenerations cost6.5E within587.5. The source counters consume all22 paired
lifecycle debts and all24 divider carry debts, free explicit classical bits,
and return current physical product owners.

## Compact endpoint binding

Use the exact compact source from
`research/stream_phase/alias_ring/phase_ledger.py`: retain p, omit c, and
replace polynomial mask32 with10 in every threshold. Thresholds5 and6 each
gain one AND; c preparation loses one. The final constant overflow is
`CZ(flags1,flags3)`. Its peak is endpoint43+two constant ones+p+threshold+
feature=48. The original compact total147Toff includes the two endpoint
frame gates. The candidate05 translation to centres(-1,-3,-7,-1,-2), omitting
only stage0 pair(0,26) in both directions, reduces that to145.

The isolated angle proxy must explicitly expect **34 generic,4 T,and0 direct
Clifford `z_pow` calls**. The inherited `(34,4,1)` assertion cannot be reused:
the last Clifford operation is now emitted as CZ. This is a changed emission
class, not an omitted phase. All generic sites, angles, flags, phase slots,
and the exact2^50 model remain unchanged and must pass the complete proof.

## Evidence and next gate

Followup003 completed in47.047seconds. First61/Q48 is an exact mathematical
survivor. Its Q49 framed alternatives75(seed0) and74(seed8) both replayPASS
but lose to frozen73 and are not selected.

The separate [candidate05 review](CANDIDATE05_REVIEW.json) freshly checks its
source pins, circuit/text digests and all48 proof chunks. All3,133,452 inputs
and all HMR transcripts are proved; each input/expected-phase digest agrees
with candidate04. Every emitted non-CSWAP line is identical to04 and exactly
two CSWAPs are removed. Its exact expectation is1560.5Toff+4T+34R atQ49,
cost88,177.87103089. This is native evidence, not official qualification.

The Q48 paper pass supports parent authorization of an isolated candidate06.
Required next steps are a width-valid table/lifecycle/compact-phase emitter,
exact native resource and ownership accounting, component debt proofs, the
full-domain all-HMR integer50 proof, and the unchanged official verifier on
default/1/2/3. No previous candidate is modified and no submission is made.
