# Repaired third-chart oracle and deterministic fixture: source review

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**Conclusion:** no algebra, scale or fixture-admission blocker found in the
two reviewed sources. This is an independent source review, with no provider
import, deterministic-fixture generation, classifier invocation, sampling,
native test or official run by the reviewer. The v6 proposal is separate
from the selected v5b composition.

## Exact reviewed sources

Both sources are under `controller_work/after_v3/blocks/v6/`:

- `boundary_scale_first3.py`: SHA256
  `03fe157840d2ccd400aab5bf73fdb46c620c416a6007aa530797cb6db524105c`.
- `prepare_zero_third_fixture.py`: SHA256
  `b34ab50ac470bd66a46b175a45c5382123b8c476b35265d431345d2fd2cd10e0`.

The review also read the unchanged field operations, old first-two boundary
scale adapter, physical-panel preparation/validation interface and complete
frozen reference classifier. Those are the exact dependencies named in the
new source's pin map; their code and predicates are not modified.

## Third-head identity, including the repaired zero

Write `A=P0(alpha2)`, `B=P1(alpha2)`, `Y=rawY2`, `a=20` and `b=18`.
Starting the ordinary query from `(Y,1)`, the first two matrix steps give

`D2=(1+A*Y)/a`, `N2=(Y+B*D2)/b`.

The unchanged admitted domain requires both values nonzero. In particular,
`1+A*Y` is a unit. For nonzero Y, the proposed nested inverse gives
`middle=Y/(1+A*Y)`. For Y=0, suppressing the added A gives `inv0(inv0(0))=0`,
so the same formula remains true. Then

`P2=b/(a*middle+B)=D2/N2`.

The denominator is a unit because N2 is a unit. At Y=0 it is B; no new raw-Y
nonzero assumption is introduced. The source compares this formula to the
ordinary matrix computation and the original physical oracle's third head.

## Changed carry and physical coefficient scale

The source rechecks the two existing special heads and the first three zero
flags, then initializes the generic query at index 3 with carry one. Every
later row applies all previous heads and the exact public inverse quadratic
differences. It checks the selected zero flag and the emitted head against
the old oracle at every index, including the padded tail.

The final nonzero carry is split into its two base-field coordinates. The
actual new gauge is computed from its low coordinate, and the selected
nonzero coordinate is used to form `selected_new/selected_old`. Multiplying
both old polynomial arrays by that ratio gives the new physical N/D boundary.
The terminal polynomial unit is unchanged because the heads and padding
recurrence are unchanged. The independent equality
`gamma=selected_new/terminal_unit=ratio*old_gamma` and the leading-D check
bind the scale convention.

Thus the oracle does not reuse the old gauge-one label or silently retain
the old final carry scale. A later production release still needs actual
coverage of its new gauge-one branch, if reachable; the report must state
the observed chart coverage rather than infer it from a previous fixture.

## Exact zero-residue construction and full admission

For a fixed physical root a, its magnitude's coefficient in raw residue 2 is

`c(a)=a*U(a)/(theta+4+a)`,

where U is the product of the 35 public irreducible quadratics. The source
computes exactly this coefficient in the common K24 chart. For distinct
roots a and b, their two base-field coordinate columns are independent:
if their ratio were in the base field, comparing the theta coefficients in
the two linear denominators would force a=b. The public nonzero factors
`a*U(a)` do not change that conclusion.

The preparer keeps the first previously saved admitted support, changes one
free magnitude through a fixed bounded list, and solves the last two
magnitudes by the exact two-by-two field determinant. It rejects zero solved
magnitudes, recomputes the full residue and requires it to be exactly zero.
No RNG or population draw is used. The newly constructed physical input is
explicitly a deterministic positive fixture, not a sampled failure estimate.

The preparer then invokes the unchanged complete `Ref.classify` and rejects
any case whose cutoff-15 union is true. This includes the finite numerator/
denominator conditions and the full half-core profile restrictions. Only
after that full-admission check does it call the old physical boundary oracle,
require raw query 2 to be zero, and require the repaired chart's queried
numerator and denominator to remain units. The prepared row retains the
exact classification and source/support/solve provenance.

This distinction matters: the unchanged key harness independently filters
its finite/key interface, but that alone would not establish the new
fixture's stronger whole-decoder admission. Here the stronger claim is
supplied by the pinned deterministic preparation and full classifier check.
The subsequent standard panel validation checks root positions, distinct
support, nonzero magnitudes and the unchanged random-mask ABI.

## Scope still open

The native component and full key checker remain their own evidence gates.
A correct deterministic fixture is not a measured gain or a population
certificate. Future composition must preserve the new carry-scale oracle,
retire every actual zero-predicate and matched inverse mask, and qualify
the complete tape and fresh original official runs. Neither this review
nor the targeted fixture changes the frozen admitted event or the selected
v5b source packet.
