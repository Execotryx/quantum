## 1. Admission

- [x] 1.1 Check the listed source locations for I1, I2 and I3. Record licence, revision and the origin's published hash, or `binary_only`. Record each hint as `match` or `mismatch`.
- [ ] 1.2 Create `third_party/invsqrt-<id>/` for each admitted candidate.

## 2. Regeneration and ordering

- [ ] 2.1 Add the vendored-invsqrt adapter with modification notices.
- [ ] 2.2 Build each admitted candidate twice. Compare with the origin's hash where one exists.
- [ ] 2.3 Compute static costs and record the verification order.

## 3. Sequential verification

- [ ] 3.1 For the next candidate in order: smoke run, then full run. Exclude on any failure and move on.
- [ ] 3.2 At the first zero-failure candidate, stop and run the fresh confirmation.
- [x] 3.3 Bank `invsqrt-v8`, or record `no_go` when the list is exhausted.

The [admission decision](../../../../docs/evidence/vendored-invsqrt/admission.md)
excluded all candidates. Tasks 1.2, 2.1–2.3 and 3.1–3.2 apply to admitted
candidates.

## 4. Records

- [x] 4.1 Dated change log and strict OpenSpec validation. Attribution for admitted sources, when applicable.
