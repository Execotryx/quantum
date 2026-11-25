# Repaired third public chart: separate v6 source candidate

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**Source preparation only. No native build, fixture generation, classifier run or population experiment has been performed for this candidate.** All queued v5 providers, checkers and source packets remain unchanged. This family depends on the separately prepared matched191/195 inverse provider. It is an alternative extractor binding, not another patch to the same inverse calls.

## Exact chart and the old admitted event

Let Y be the raw common-extension residue at public index2. Evaluate the two earlier coefficient heads at that node, obtaining A and B. The fixed quadratic differences are a=20 and b=18. The ordinary two query steps with incoming carry1 give

\[
 n_1=(1+AY)/a,\qquad d_1=Y,\qquad
 n_2=(Y+B n_1)/b,\qquad d_2=n_1.
\]

The already admitted active third denominator and numerator are nonzero. Thus 1+AY is nonzero and aY+B(1+AY) is nonzero. The earlier active heads are nonzero polynomials of degree at most one; at an irreducible quadratic node their evaluations A and B are units. None of these conditions implies that raw Y is nonzero.

The unrepaired inversion chain fails at Y=0. For example, the locally valid choice A=B=1 gives the true head b, while the uncorrected chain gives b/(a+1). This is a local query-domain example, not a newly sampled physical syndrome or a claim that a particular whole physical regression case has that data.

The new chain computes the real quantum bit z=[Y=0], then applies

\[
Y\mapsto\operatorname{inv}_0(Y)
\mapsto\operatorname{inv}_0(Y)+(1+z)A
\mapsto u=\operatorname{inv}_0\bigl(\operatorname{inv}_0(Y)+(1+z)A\bigr)
\mapsto au+B\mapsto (au+B)/b\mapsto b/(au+B).
\]

For Y nonzero, u=Y/(1+AY). At Y=0 the suppressed addition makes u=0, which is the same formula. Since au+B=(aY+B(1+AY))/(1+AY), the final inverse argument is a unit under the old numerator condition. The emitted result equals d2/n2 for every old-admitted input, including the zero raw residue and the special case a+AB=0. The first and middle inverses deliberately allow zero; their retained-norm provider proves the zero-extended inverse contract.

The return undoes the final inverse, multiplies by b, adds B and divides by a. This exposes u before any other query. The predicate zero(u)=zero(Y) is therefore the exact prefix HMR source. After paying that saved mask, the return undoes the middle inverse, adds A only when the live predicate is zero, and undoes the first inverse. Every saved child-norm mask is paid by its own matching191/195 inverse pair. Each earlier coefficient head is restored immediately after its public node view.

## Quantum ownership and phase debts

The production first-two adapter already has840 residue/head bits and24 constant-one carry bits. It constructs the existing tail controller, whose initial predicate is an explicitly allocated zero bit unused before index15. The new prefix turns carry1 into a clean24-bit bank with one public X, uses the three first-two inverse calls and three third-chart inverse calls, then restores carry1 before generic extraction begins at index3.

The third chart borrows the existing initial tail predicate. It computes z, uses it for one24-bit conditional head addition, HMR-resets it into its actual classical mask and leaves the physical allocation with the tail controller. It does not free or relabel that wire. The prefix boundary checker requires this same initial tail bit to be zero before generic use. Peak ownership is840+24+1 retained bits plus24 fresh helper bits, hence Q889.

The generic return ends at index3, restoring its raw residue and public carry1. The tail closes before the special charts return. The new return creates its own zero predicate only after these owners have released the old flag. Its maximum is864 retained bits plus one return predicate and24 fresh inverse helpers, again Q889. The carry bank returns to zero after every inverse and is restored to1 before its original owner frees it.

The third prefix retains three actual six-bit child masks plus one actual zero-predicate mask. The first-two prefix retains its own18 bits, for37 pending special classical bits total. The prefix zero mask is paid once by CZ at the reconstructed return predicate. The fresh return predicate is HMR-erased after raw Y is restored and paid by the unchanged classically conditional22T zero phase. This adds exactly one fresh-bit event, with mean11. There is no measurement-outcome assumption or free predicate query.

## Complete incremental ledger

| Removed ordinary work | Static T |
|---|---:|
| Two query products in each direction at index2 |396 |
| Nested-norm division prefix |291 |
| Shared return including restoration of the next pending input |543 |
| Next input scale at index3 |99 |
| **Removed total** |**1329** |

| New work | Prefix T | Return T |
|---|---:|---:|
| Three matched inverse calls |573 |585 |
| Real24-bit zero query |23 |23 |
| Conditional24-bit earlier-head addition |24 |24 |
| Fresh return zero-predicate phase |0 |22 |
| **New total** |**620** |**654** |

Thus the new pair costs1274 static T, saving55. The prefix increases by32 and the return decreases by87. The removed mean is1329-27/4096-84/2^24; the new mean is1274-12/64-22/2=1262.8125. The exact incremental saving relative to the matched first-two candidate is277582827/4194304=66.18090319633484 mean T.

Including the already separate matched first-two change, the key source model is216928 paired static T and101087 prefix T. Its exact expected delta from frozen v4 is-1310167980/4194304; no new value from an official run is implied. The key event Counter changes to32 direct84 events,66 inverse27 events, seven scalar4 events, one last-return child15 event, one gauge10 event and21 zero-flag22 events. The prefix debt's zero-T CZ adds no separate discount.

## Carry scale and domain transfer

Generic index3 starts with public carry1 and raw residue3, so its input scale is omitted. All later heads and real zero predicates remain identical: queried numerator/denominator pairs are multiplied by a common nonzero carry ratio. That ratio is nonzero because the old third queried numerator was a unit. Synthesis therefore changes only its common nonzero base-field scale selected from the final carry. The preimage/finish and admitted-event common-scale arguments remain applicable after native/source qualification.

The new `boundary_scale_first3.py` independently checks both special heads, the repaired third head, every later head and tail flag, and recomputes the final carry, selected half and numerator/denominator scale from the original physical oracle. An old gauge-one fixture is not automatically a gauge-one fixture in this chart. The physical checker retains that old case, reports actual new gauge coverage honestly and offers `--require-gauge1` as an explicit extra gate. Missing new physical gauge-one coverage is not silently inferred from the old label.

## Prepared native gates

`check_third_pivot_chart.py` constructs an open620T prefix and a fully closed1274T pair, each twice, with three HMR seeds. Full input coverage is20480 component cases across complete base and extension axes, arbitrary extension values,4096 deliberately zero raw residues, and4096 cases with a+AB=0. All require the original third query's two coordinates nonzero. The direct polynomial0x1053 oracle uses the ordinary two matrix steps, independently of the repaired chain. The pair checks all data, dirty bystanders, owned bank and scratch, arbitrary diagonal masks and three nonlinear probes. Fixture-only classical copies observe the actual three return child masks and return predicate mask, independently reconciling every executed T count. Alias/type and invalid return-record rejection happen before nonlinear emission.

`prepare_zero_third_fixture.py` is a separate root-only deterministic construction. It keeps the support of one old fully admitted physical fixture, varies one magnitude through a fixed bounded list and solves the last two magnitudes from the two linear equations for raw residue2=0. Distinct physical roots give independent residue columns. It rejects zero magnitudes or any failure under the unchanged full classifier, then requires the unchanged physical oracle and new carry oracle to agree. No population sampler or new statistical claim is used. If the bounded list does not produce a valid case, preparation fails without a success package.

The production checker keeps781 old key-admitted physical fixtures, the old rare gauge fixture, the76 explicit old exclusions, and the constructed physical raw-zero fixture. It builds four tapes twice: key prefix, paired key, prefix carry/tail-bit boundary before generic3, and return carry boundary after generic3/tail closure. Complete paired phases and all source/scratch restoration are checked over three seeds. The original and new boundary oracles have explicit independent roles. `KEY_CHECKER_DERIVATION.json` records all32 literal changes from the immutable matched-first-two checker; no old file is edited.

## Root-only commands

First prepare the deterministic physical fixture under the shared guard:

```sh
/usr/bin/python3.13 -B controller_work/after_c5/root/guard_wait.py \
  --log controller_work/after_v3/blocks/v6/runs/third-raw-zero.guard.json \
  --stdout controller_work/after_v3/blocks/v6/runs/third-raw-zero.stdout \
  --rss-soft 1500000000 --reserve 4000000000 -- \
  /usr/bin/python3.13 -B controller_work/after_v3/blocks/v6/prepare_zero_third_fixture.py \
  --output controller_work/after_v3/blocks/v6/runs/third-raw-zero
```

Component smoke:

```sh
/usr/bin/python3.13 -B controller_work/after_c5/root/guard_wait.py \
  --log controller_work/after_v3/blocks/v6/runs/third-chart-smoke.guard.json \
  --stdout controller_work/after_v3/blocks/v6/runs/third-chart-smoke.stdout \
  --rss-soft 3000000000 --reserve 4000000000 -- \
  /usr/bin/python3.13 -B controller_work/after_v3/blocks/v6/check_third_pivot_chart.py \
  --per-mode 32 --output controller_work/after_v3/blocks/v6/runs/third-chart-smoke
```

The full component uses4096 per mode and fresh third-chart-full paths. Production smoke:

```sh
/usr/bin/python3.13 -B controller_work/after_c5/root/guard_wait.py \
  --log controller_work/after_v3/blocks/v6/runs/first3-smoke.guard.json \
  --stdout controller_work/after_v3/blocks/v6/runs/first3-smoke.stdout \
  --rss-soft 3000000000 --reserve 4000000000 -- \
  /usr/bin/python3.13 -B controller_work/after_v3/blocks/v6/check_first3_retained_norm_adapter.py \
  --smoke --output controller_work/after_v3/blocks/v6/runs/first3-smoke
```

The full production gate omits `--smoke` and uses fresh first3-full paths. Add `--require-gauge1` only when a genuine fixture under the new carry chart is present; otherwise its explicit failure requests that missing coverage rather than altering a quantum promise. Every gain remains pending these native gates, a complete new emitted circuit and four original official salts.
