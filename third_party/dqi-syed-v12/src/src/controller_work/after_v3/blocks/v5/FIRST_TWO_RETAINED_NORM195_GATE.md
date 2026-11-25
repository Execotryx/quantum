# First-two retained norm stack: 195T source gate

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**Prepared and source-reviewed algebra; native qualification is pending.** This is a separate production-only candidate. It preserves the frozen v4 source and the prepared, unrun 63T contraction and 218T alternatives. No complete decoder gain, official result or new population experiment is claimed.

## Exact closed inverse

Write the production K24 source as S=a+b*theta over F=GF4096, with theta^2+theta+2048=0 and the original F polynomial basis0x1053. Define N=a^2+ab+2048*b^2. The caller supplies24 owned, initially zero bits partitioned into N (12), h (6) and gamma (6). These are retained data, never allocator scratch and never freed by the component.

Convert N to the existing quadratic GF64 chart N=L+R*tau, with its fixed extension constant delta. Set h=L^2+LR+delta*R^2 and gamma=inv0(h). The existing source-preserving20T cubic GF64 inverse computes gamma directly into its owned bank and closes all ten temporary parents. Form the fresh twelve-bit inverse norm Z=((L+R)*gamma,R*gamma) in that chart, then return Z and N to polynomial encoding.

Consume each source half into its product with Z. Their two actual old-value HMR masks are repaid by the unchanged bilinear phase using the current half and retained original N. This is exact because (a/N)*N=a and (b/N)*N=b; when N=0, the field norm implies a=b=0. Both debts cost zero T. There is no source-half nonzero promise.

The remaining debt order is fixed:

1. Convert original N back to its quadratic12 chart and HMR that owned bank. If the inverse norm is Z=X+Y*tau, the original tower coordinates are ((X+Y)*h,Y*h). Convert Z to that chart, temporarily conjugate its first half, pay the first six mask bits with (X+Y)*h, undo the conjugation, then pay the second six bits with Y*h. These are exact bilinear phases at zero T, also at zero.
2. Convert h to the existing quadratic6 chart and HMR its six owned bits. The mask therefore belongs to tower(h), not polynomial(h). The existing scalar_inverse_phase.phase_inverse_six(gamma,mask) expects exactly this mask ABI and pays it using inv0(gamma)=h. Gamma remains polynomial and unchanged. This phase costs4 T if that actual six-bit HMR mask is nonzero and0 otherwise.
3. Erase the owned gamma bank from the quadratic norm of Z: Norm12(Z)=gamma. The existing eraser HMRs this target and pays its exact quadratic/linear debt at zero T. It does not free the owned bank.
4. Restore Z to polynomial encoding, conjugate the scaled K24 halves to obtain S^-1, and erase the fresh Z from Norm24(S^-1)=inv0(N). Free only this locally allocated twelve-bit output.

All24 owned bits have returned to zero. Every inverse is the zero-extended inverse inv0, so the all-zero source is retained. The cubic child scaffold, both old half masks, original norm mask, child norm mask, child reciprocal mask and final inverse-norm mask are each paid against the named restored/retained witness before that witness changes.

## Public production ownership

The production key starts its carry at the public constant1. The exact generic reverse extractor loop ends with public index2, restoring the original third query and that incoming carry. The tail controller closes before the three special first-two inverses. No remaining first-two operation reads the carry, and its owner resets/frees it only after all three returns.

The new production adapter therefore applies X to carry bit0 at this seam, making all24 owned bits zero. It calls the new closed inverse three times, requiring every storage bank reset after every call, then restores X on bit0 before returning to the original owner. The old first-two mask repayments and public coordinate transforms remain in their original order. The intermediate source record explicitly declares this production constant-one contract.

This does not make an arbitrary quantum carry clean. The immutable old component supports a larger arbitrary-unit-carry extension; its fixtures and claims remain separate. The new physical checker uses the existing781 admitted physical key fixtures plus the actual rare gauge-one fixture, and retains the original76 exclusions. No new input exclusion is introduced.

## Lifetime and nonlinear count

| Span | Owned storage live | Fresh helpers | T |
|---|---:|---:|---:|
| Compute original K24 norm | N12 |0 |42 |
| Compute child norm in N's quadratic chart | N12+h6 |0 |15 |
| Existing cubic child reciprocal | N12+h6+gamma6 |10 temporary parents |20 |
| Form inverse norm | all24 |12 inverse-norm output |30 |
| Consume two source halves | all24 |12 inverse norm+12 product temporary |84 |
| Repay two old half masks and HMR original N | h6+gamma6 |12 inverse norm |0 |
| Repay child HMR mask | gamma6 |12 inverse norm+at most6 scalar work |4 or0 |
| Erase gamma and inverse norm | shrinking owned stack |12 inverse norm, then0 |0 |
| **Closed inverse** | **24 separately owned zero inputs, restored** | **maximum24** |**195 static** |

At the actual production seam the retained bank is840 query bits+24 carry bits=864; the local maximum is888. The isolated checker deliberately adds an arbitrary retained bystander to865 and must observe Q889. Earlier unchanged production spans keep the whole key maximum at Q889. No supplied inverse, bank bit or classical mask is omitted from the ownership ledger.

The exact executed closed-inverse count is `191+4*[actual child HMR mask != 0]`, with source expectation `195-4/64`. Replacing the selected v4 closed inverse `276-84/2^24` three times saves243 static T and exactly 1020002241/4194304 mean T (243.18748497962952). The new key source count is216986 static T; the prefix remains101058. Its exact mean model is 909157644619/4194304 (216760.0738093853), obtained independently from the existing actual event ledger.

The existing Events.install wrapper already records scalar_inverse_phase.phase_inverse_six and its aliases. The candidate is imported before installation. No additional event is manually recorded. The full new key must contain exactly these events:

| Event | T removed on zero mask | Mask bits | Occurrences |
|---|---:|---:|---:|
| direct_carry84_selected_target_parities |84 |24 |33 |
| inverse_phase27_12_helpers |27 |12 |67 |
| last_return_child_norm_guard |15 |6 |1 |
| scalar_inverse_six |4 |6 |4 |
| tail_or_gauge_fresh_zero_phase |10 |1 |1 |
| tail_or_gauge_fresh_zero_phase |22 |1 |20 |

The three old retained-child30 and outer54 events disappear. The four scalar events are one unchanged last-return event plus exactly three new child repayments. The checker requires the whole multiset and its exact Fraction expectation, preventing duplicate accounting.

## Prepared native gates

The isolated checker has three panels: closed prefix, closed pair, and the actual old deferred inverse followed by the new closed inverse and repayment of its original source masks. Each panel has two identical builds and three HMR seeds. The full fixture set has20480 cases: all4096 base-axis inputs, all4096 extension-axis inputs, all4096 equal-half inputs,4096 fixed arbitrary K24 inputs, and4096 repeated zero inputs. The base-axis norm traverses all4096 values; this is not an exhaustive2^24-source claim.

The oracle performs independent physical polynomial multiplication/inversion. Every original source value, all24 separately registered clean bank bits, arbitrary dirty bystanders, classical probe bits, unowned scratch and nonlinear phase are checked. Three cubic probes supplement an arbitrary classical diagonal phase. A fixture-only classical CX copies the actual six-bit child HMR mask into an output register; it neither forces nor changes the outcome. Per-shot aggregate T is checked exactly by subtracting4 for each observed zero mask. Invalid source length, bank length, aliases, classical storage and extension choices must fail before emission.

The production checker retains the frozen v4 preservation gate and unchanged independent physical-key oracle. It builds prefix, paired-key and public-carry-seam tapes twice. The seam tape observes all24 carry bits equal1 before the public X, and checks clean unowned scratch. Its first-two HMR debts are intentionally still open, so this intermediate panel checks values only. The full paired key checks all original syndrome data, arbitrary diagonal and cubic probes, scratch and phase. It requires exactly three new receipts, the full event multiset above, actual new loaded-source identities and unchanged old source bytes. It does not temporarily rebind an old provider merely to satisfy a preservation assertion.

## Root-only commands

These commands are prepared, not executed. Use one shared guarded job at a time. First run the isolated smoke:

```sh
/usr/bin/python3.13 -B controller_work/after_c5/root/guard_wait.py \
  --log controller_work/after_v3/blocks/v5/runs/norm-stack-smoke.guard.json \
  --stdout controller_work/after_v3/blocks/v5/runs/norm-stack-smoke.stdout \
  --rss-soft 3000000000 --reserve 4000000000 -- \
  /usr/bin/python3.13 -B controller_work/after_v3/blocks/v5/check_inverse_retained_norm195.py \
  --per-mode 32 --output controller_work/after_v3/blocks/v5/runs/norm-stack-smoke
```

The full isolated command substitutes `--per-mode 4096` and fresh `norm-stack-full` paths. After the isolated gate passes:

```sh
/usr/bin/python3.13 -B controller_work/after_c5/root/guard_wait.py \
  --log controller_work/after_v3/blocks/v5/runs/first2-stack-smoke.guard.json \
  --stdout controller_work/after_v3/blocks/v5/runs/first2-stack-smoke.stdout \
  --rss-soft 3000000000 --reserve 4000000000 -- \
  /usr/bin/python3.13 -B controller_work/after_v3/blocks/v5/check_first2_retained_norm_adapter.py \
  --smoke --output controller_work/after_v3/blocks/v5/runs/first2-stack-smoke
```

The full physical-key command omits `--smoke` and uses fresh `first2-stack-full` paths. A component pass alone does not bank a whole-circuit improvement; a new complete emitted tape and four full original salts remain required.

## Preserved alternatives

The prepared63T phase-contraction provider and its two checkers remain unchanged and unrun. The218T original-norm provider reuses the existing65T source-preserving reciprocal, and its generic checker and production adapter remain unrun. The219T copy recipe is algebra only. None is counted as measured or used to supplement the195T ledger. They remain reproducible fallbacks if this stronger candidate fails a concrete gate.
