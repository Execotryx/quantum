# Regenerated public DQI candidate field

D4 and D5 each reproduced the full SHA-256 published by its pinned
origin in two independent Linux builds. The stage-one verifier field
uses these exact bytes.

| Candidate | Qubits | Static Toffoli-like gates | Circuit bytes | Peak RSS across the two runs |
| --- | ---: | ---: | ---: | ---: |
| D4 | 897 | 444,667 | 542,515,630 | 2,159,388 KiB |
| D5 | 880 | 906,693 | 722,541,720 | 1,536,076 KiB |

D4 took 137.43 and 142.62 seconds under Python 3.13.15 and NumPy 2.3.5.
D5 used the same Python version and its upstream NumPy 2.5.4 pin.
The reported RSS figures are GNU time's maximum resident set sizes.
The pricing receipts will record mean executed Toffoli-like gates.

[Admission](evidence/vendored-dqi/admission-20261114.json) ·
[D4 rebuilds](evidence/vendored-dqi/d4-regeneration/) ·
[D5 rebuilds](evidence/vendored-dqi/d5-regeneration/)
