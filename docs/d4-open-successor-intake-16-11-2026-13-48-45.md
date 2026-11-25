# D4 open successor intake and preflight

Downloaded the pinned Syed v12 source archive, publisher manifest and
license. All 431 extracted files matched their internal manifest, with
the internal manifest itself covered by the published archive hash.
The extracted inventory passed the competition-asset and denylisted
hash checks. The source remains isolated during build reproduction.
The reference D4 artifact matched its v8 member record and both
historical comparison registrations were pinned.

The native preflight driver reuses the archived batch reconstruction
and verifier diagnostics. It expects four original and two residual
capture batches, generates one known-support fixture for every weight
from 0 through 35, and checks four separately specified mixed-pole
inputs. The zero-slope witness is validated against the independent
scalar chart. It compares two alternate masks and simulator seeds
on the targeted set and two 4,096-shot matched panels on the whole
circuits.

The inspected source documents a weight cutoff of 15, active finite
numerator and denominator residues, and restrictions on degree drops
and paired gaps. These are source assumptions to challenge with the
fixture suite. A representative panel alone may sample none of these
edge cases. The native report separates their phase and cleanup results
from the representative-panel price screen.

## Independent rebuilds

Both isolated Ubuntu builds used CPython 3.13.15, the hash-locked
NumPy 2.2.4 dependency and the pinned native backend. They produced
byte-identical 455,590,024-byte KMBs at the published SHA-256
`7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9`.
The upstream build reported 889 declared qubits and 384,003 static
Toffoli-like operations. Both source inventories matched all 132
runtime entries against the extracted source or the pinned official
Kickmix library. The common source-map hash was
`44b7cc795a3bc9ab4da9396e67c84bac1dc156587aa1a03ed8c7c96427512315`.
The memory guard observed peak summed group RSS of about 0.97 GiB
in each build. The source tree stays staged while the correctness
screen runs.

[First build](evidence/d4-open-successor-20261116/build-a.json) ·
[Second build](evidence/d4-open-successor-20261116/build-b.json) ·
[Native preflight registration](evidence/d4-open-successor-20261116/preflight-registration.json)

## Native results

Banked D4 reproduced its four historical phase offsets and one
additional phase offset in the residual replay. Syed v12 cleared all
1,536 shots from the six captured batches, including all passing
controls, with zero value, phase, dirty-scratch or mask offsets.

The two 4,096-shot panels were clean for both roles. Banked D4 averaged
430,821.43 and 430,822.60 executed Toffoli-like operations per shot.
Syed v12 averaged 383,155.36 and 383,156.92. Its maximum panel mean,
889 qubits and the minimum historical repetition factor give a
development preflight estimate of about 362.39 billion, 12.64% below
the historical banked price.

With two different simulator seeds and both random and zero masks,
Syed v12 passed the 21 fixtures at weights 15–35 and all four mixed
pole fixtures. Every weight-1 through weight-14 fixture failed syndrome
restoration and the weight-0 fixture had an incorrect phase. Scratch
and mask ownership checks stayed clean in these targeted failures.
The exact weight boundary agrees with the original source cutoff.
The native correctness gate failed, so the v12 historical replay and
resource gains do not qualify it for an official comparison.

[Native preflight](evidence/d4-open-successor-20261116/native-preflight.json)

## Cloud reproduction

The existing VM replayed the registered inputs from a RAM-backed
stage. The VM verified the launcher and input package hashes. The
83-second run produced a report byte-identical to the local report
at SHA-256
`ecfc6cdb92814ac8a59549f32a3d959d5297a04a6ad5f8ec78a1fce632f25178`.
The collected archive matched the VM checksum
`85b7a732b394bac07984a3132fb3d38915bfdf698ea042891eff3f31d1798c97`.
Its status zero records successful completion of the preflight.
The report's false correctness gate records the targeted failures.
Compute Engine confirmed the VM was terminated after receipt collection.

[Cloud report](evidence/d4-open-successor-20261116/cloud-preflight/native-preflight.json) ·
[Run log](evidence/d4-open-successor-20261116/cloud-preflight/run.log) ·
[Receipt archive hash](evidence/d4-open-successor-20261116/cloud-preflight/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-open-successor-20261116/cloud-preflight/vm-stop.json)

[Intake evidence](evidence/d4-open-successor-20261116/intake.json) ·
[OpenSpec checklist](../openspec/changes/screen-open-dqi-d4-successor/tasks.md)
