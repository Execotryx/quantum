# Third-pivot component and production checker source review

Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0. Credits: Opus and Astra.

## Conclusion and scope

No source blocker was found in the held third-pivot component checker or
the production key checker at the hashes below. This review extends the
earlier emitter and adapter review; it does not replace a native component,
key, joined decoder, or official-run gate. No project module was imported,
no fixture was generated, and no circuit was built or simulated during
this review.

The independent review of the changed boundary oracle and deterministic
zero-residue fixture construction is assigned to the cost auditor. This
note reviews how those inputs are consumed and how their coverage and
ownership claims are checked. Their algebra is not independently certified
a second time here.

## Exact sources

| File under `controller_work/after_v3/blocks/v6/` | SHA256 |
|---|---|
| `third_pivot_chart.py` | `0a788b7b49b80f8d267d05ac1dc6c067fdb626aaa054d076ce3052948af32166` |
| `first3_retained_norm_adapter.py` | `6d66d5b5a308e56c50fe628cf0cfecda944db7e9189891d32ab628808d1e4cc8` |
| `check_third_pivot_chart.py` | `b570fabe7e193827c91ae00290bb85ea74d7d91a03200b1dfcbe9cae34802104` |
| `check_first3_retained_norm_adapter.py` | `3795553ea5ec70155d443a24d90930b9e32b8727d2f15abb98246edec33b4b17` |

The matched inverse provider remains
`blocks/v5/inverse_retained_norm_deferred.py`, SHA256
`8cb8eaee9312acc81a3048072ec3ddf721399ba8ccdd7eac94002f9d4ec2da46`.
The earlier emitter review is
`k24/THIRD_PIVOT_CHART_EARLY_SOURCE_REVIEW.md`, SHA256
`93401e191492278851b401f5e59842ad0defb151ea3c3d17a3cca0f06f186262`.

## Component oracle and observed phase debts

The component checker uses an independent polynomial-basis implementation
of the base field, the quadratic extension with delta2048, and two ordinary
query matrices. It obtains the expected head by performing those two
matrices and dividing their final coordinates. It does not reproduce the
new three-inversion chain to define the expected answer.

Both queried coordinates must be nonzero, as in the existing active third
pivot domain. The raw third residue itself may be zero. The five fixture
groups include both base-field axes, arbitrary quadratic-extension values,
forced raw zero, and the zero cross-coefficient case. Earlier heads are
converted into the coefficient chart expected by the emitter. The final
division, source preservation, arbitrary dirty bystanders, zero owned bank,
classical probes, and all scratch wires are checked.

The prefix is intentionally phase-open. Its three six-bit child masks and
one zero-predicate mask are actual HMR outcomes, copied only to classical
observation registers. The pair observes the three additional child masks
and the fresh return predicate mask. Its exact executed count is checked as

\[
1274+3
-4\sum_{i=3}^{5}[m_i=0]
-22[f_{\mathrm{return}}=0]
\]

per shot, where the extra3 are the deliberately inserted cubic probes.
The prefix count is620 with no conditional cleanup discount. The indices
are important: prefix child masks are paid at matched reciprocal witnesses
with Clifford corrections; only the three fresh return masks invoke the
four-T scalar phase. The prefix zero mask is paid at the restored middle
zero predicate; only the fresh return predicate invokes the22-T phase.

The component has864 retained wires, including its24-bit owned zero bank.
It borrows one existing zero predicate during the prefix, observes that it
was HMR-reset, and lets the owner free it before the return. The return
allocates a separate predicate at the actual seam. At most889 physical
qubits are allowed, and the checker verifies the native peak rather than
deducing it from the source assertion alone. Eight malformed ownership or
shape contracts must fail before a nonlinear gate is emitted.

Each prefix and pair tape is built twice. All three HMR seeds are exercised.
The expected paired phase includes an arbitrary full864-bit diagonal probe
and three cubic probes involving both earlier heads, the changed current
word, and dirty bystanders. No phase-zero assertion is made for the open
prefix.

## Production ownership and fixture scope

The production checker starts from the accepted v4 loader and preservation
gate. It replaces only the extractor provider for this isolated key test.
The old next-word return, last-return arithmetic, scalar seed, synthesis,
tail implementation, and original key harness remain the selected v4
providers. Provider identities are asserted before emission and again at
the end.

The fixture set is the original781 selected key cases, the existing rare
physical case, and one deterministically constructed raw-third-zero case:
783 selected cases in total, with the original76 key-domain exclusions
retained. The original fixture files have exact fixed hashes. The added
fixture must match its preparation receipt, and the receipt's source
bindings are rehashed. The unchanged key harness recomputes physical
syndromes, classification, and the old polynomial boundary oracle. The new
boundary adapter must independently replay every unchanged head and flag
and derive the changed common scale. The checker directly compares its
raw-zero label to the old oracle's actual third raw query.

The key-only harness filters the finite/key domain, not the half-converter
domain. Consequently, the stronger statement that the newly constructed
zero-residue fixture is admitted by the complete old classifier comes from
the separately reviewed deterministic preparation proof and receipt. The
checker does not silently convert all original key-domain cases into
complete-decoder admitted cases.

Two intermediate tapes check the clean-bank promise on physical inputs.
The prefix tape is captured after the three special charts and restoration
of carry1. It has865 retained wires and checks that the initially owned tail
predicate at physical index864 is zero. The return tape is captured after
the generic reverse loop and `tail.close()`, before any special closing
inverse. It has864 retained wires. Both tapes check all24 carry bits against
the public constant1, preserve the classical probes, and require every
nonretained scratch wire to be zero. Both remain explicitly phase-open.

The loan is therefore the actual24-bit carry after a public X reset; it is
not an arbitrary or dirty initial-carry promise. All six matched inverse
records and the separate prefix zero mask must be retired before final
restoration. The full paired key restores all840 original syndrome bits,
all probe bits, and every scratch wire, and checks the original harness's
arbitrary865-bit diagonal and three cubic boundary phases.

The changed carry can change the final gauge. The report records actual
new gauge coverage and never reuses an old gauge label as proof of new
gauge1 coverage. The optional `--require-gauge1` fails if no actual new
gauge1 fixture is present. Any later whole-candidate gate must preserve this
qualification and supply the required positive if it demands that chart.

## Counts and event ownership

The full key model is216928 static T with prefix101087, Q889. Its complete
event multiset is checked, rather than inferred from a difference of means:

| Event | Conditional T | Mask bits | Calls |
|---|---:|---:|---:|
| Direct-carry selected-target phase |84|24|32|
| Inverse phase with12 helpers |27|12|66|
| Last-return child-norm reconstruction guard |15|6|1|
| Scalar inverse-six phase |4|6|7|
| Gauge zero phase |10|1|1|
| Tail or third-chart zero phase |22|1|21|

These entries give the exact fresh-mask expectation
`28402108715/131072`. The change against selected v4 is
`-327541995/1048576`; the incremental change against the matched first-two
chart is `-277582827/4194304`, with a55-T static reduction. These are source
expectations, not observed official prices. The bounded review independently
recomputed the fractions with the standard-library `Fraction` type.

The production checker requires two identical copies of all four tapes:
key prefix, full pair, prefix carry seam, and return carry seam. Its full
run retains the three existing seeds and all783 fixtures. Smoke mode is
explicitly marked incomplete and includes actual zero-residue cases; a
later gate producer must require the full mode and contiguous seed coverage.

## Review actions

The review read the two complete checker sources, the two emitters, the
matched inverse provider, v4 provider/event bindings, and the unchanged key
harness. It compared the new checker to the matched first-two harness,
checked exact source hashes, AST-parsed the four held files, and recomputed
only the small rational ledger. It ran no checker, source gate, fixture
construction, native operation, random draw, or heavy job. Native component
and full key results remain pending at the conclusion of this source review.
