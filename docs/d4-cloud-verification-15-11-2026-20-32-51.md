# D4 extraction repair cloud verification

The reversible projective repair in `repair-d4-extraction-poles` cleared
all four historical phase errors in the original 1,024 matched shots.
Both builds produced the exact same KMB. The four passing controls
stayed clean, and the repaired batches recorded zero value, phase,
mask, or scratch errors.

The registered cloud comparison ran 102,400 official shots per draw.
Each circuit passed all eight draws. The same eight salts were used for
both circuits, and the verifier derived independent shot streams from
each circuit hash. The matched historical replay provides the same-input
comparison.

| Measurement | Repaired D4 | Banked D4 |
| --- | ---: | ---: |
| Official draws passed | 8 / 8 | 8 / 8 |
| Shots | 819,200 | 819,200 |
| Value errors | 2 | 0 |
| Phase errors | 0 | 0 |
| Declared qubits | 4,081 | 897 |
| Static Toffoli-like gates | 3,243,349 | 444,667 |
| Average executed Toffoli-like gates | 3,198,379.19 | 430,822.88 |
| Pooled priced failures | 1 | 1 |
| Pooled cost | 63,747,071,243,053.88 | 414,840,001,725.70 |

The two candidate value errors occurred on draws 6 and 7. The official
receipt records aggregate error counts and does not identify their
physical cause. The prototype uses wide coefficient banks to retain
the reconstructed polynomial and keeps unsupported cases visible to
the verifier. The prototype is retained as repair evidence. Banked D4
remains the selected circuit because the prototype costs 153.67 times
as much under the pooled metric.

The first launch failed during circuit serialization with 670 MiB free
on the boot disk. The retry put the 818,415,490-byte candidate and its
temporary files in memory, with the original artifact and registration
hashes intact. The retry ran 80 minutes 25 seconds, from 14:08:09 through
15:28:34 UTC. The VM had a three-hour automatic stop period and was
confirmed terminated at 15:32:26 UTC after receipt collection.

The downloaded archive SHA-256 matches the VM's checksum
`422d174ad5442fbb8925f4d9c9bc6a1013f7e9e3ad4579ccc3953eead2d5e187`.
The offline audit verified the identities and hashes of all 16 draws and
recomputed both pooled costs in the pinned Linux environment.

[OpenSpec checklist](../openspec/changes/repair-d4-extraction-poles/tasks.md)
? [Registration](evidence/d4-extraction-repair-20261115/full-cloud-registration.json)
? [Matched replay](evidence/d4-extraction-repair-20261115/full-matched.json)
? [Repaired receipts](evidence/d4-extraction-repair-20261115/full-cloud/campaign/candidate/summary.json)
? [Banked receipts](evidence/d4-extraction-repair-20261115/full-cloud/campaign/banked/summary.json)
? [VM stop](evidence/d4-extraction-repair-20261115/full-cloud/vm-stop.json)
