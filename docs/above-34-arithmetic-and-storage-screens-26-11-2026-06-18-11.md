# Arithmetic and storage screens

The portfolio preflight now serializes the largest ANGLE member through the
native verifier's binary buffer path before starting the long benchmarks.
This exercises the temporary-file write that failed on the full cloud boot
disk. The real archive produced byte-identical structural evidence with the
check enabled. A regression test reproduces the write failure at the preflight
boundary.

| Development screen | Observed result |
|---|---|
| Inverse-square-root affine compression | The frozen 37-wire prefix reached rank 37 modulo the constant on 2,816 legal inputs sampled across all bit lengths. The pinned native simulator returned identical values with two measurement seeds. An affine renaming through that boundary cannot lower its span. |
| Inverse-square-root small rotations | The one-shot full-domain control passed 3,133,452 inputs. Each of the three smallest rotation removals exceeded its phase tolerance. |
| Phase coefficient refit | A separate all-zero-measurement branch replay reproduced the control's 99.94718% tolerance use at input 252. For each removal, constrained refitting of the other rotations exceeded tolerance on its active constraints. The smallest-removal lane had an active-set objective of 1.04810. |
| DQI reset scheduling | The conservative projection moved 40,873 resets while preserving measurement order. Both the original and projected schedules still peaked at 900 qubits. |
| Chemistry basis order | The matched basis and weight permutation passed the decoded accuracy and gap checks. The structured five-word compiler rose from 3,632 to 4,014 static Toffolis per pass. |

[Native affine witness](evidence/aggregate34-20261126/invsqrt-stratified-affine-witness.json)
[Rotation screen](evidence/aggregate34-20261126/invsqrt-rotation-trim-v2/registration.json)
[Refit screen](evidence/aggregate34-20261126/invsqrt-rotation-refit/registration.json)
[DQI reset screen](evidence/aggregate34-20261126/dqi-reset-advance-profile.json)
[Chemistry permutation](evidence/aggregate34-20261126/chem-fixed-basis-permutation.json)
[Chemistry projected count](evidence/aggregate34-20261126/chem-permuted-structured.json)

The exact affine-conjugation screen found zero mergeable adjacent Toffoli
pairs across the public inverse-square-root member and all 15 ANGLE loaders.
The four-word chemistry pairing trial reached its bounded search level, but
the compiler could not extract a valid plan from the priced span. Its
five-word control hit the same extraction failure. Both attempts remain
development evidence.
[Pair census](evidence/aggregate34-20261126/adjacent-affine-toffoli-pairs.json)

Pyright reported zero diagnostics on the implementation files and focused
tests. The suite passed 33 cases and the OpenSpec change passed strict
validation.
