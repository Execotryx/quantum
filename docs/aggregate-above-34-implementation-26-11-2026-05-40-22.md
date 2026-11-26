# Above-34 portfolio implementation

## Certification

The new `portfolio-v2` gate requires each of the three benchmark families to
bind a source manifest, two build receipts and the exact member hashes. The
preflight derives the ANGLE loader count and chemistry coverage from the
emitted layout. Both complete runs must score strictly above 34 with the
registered archive. The archived 26.78 certificate replayed byte for byte with
SHA-256 `26c98d6a967c0fe41cc2b584b06425d4f8683ba251d2587b2c6ce2cf6ff4d8dd`.

## Development evidence

| Lane | Measured outcome | Evidence |
|---|---|---|
| Independent builds | Two isolated runs reproduced all 18 published members of Tony Li's version 2 parent exactly. The package restores circuit assembly and parameters. The comparison archive uses different members. | [Build hashes](evidence/aggregate34-20261126/tonylica-builds.json) |
| Inverse square root | Reset reuse and exact symbolic replay left the tuned reference at 37 qubits. One static Toffoli-like instruction was removed with equal total executed counts, phase and restoration over 4,096 matched native trajectories. The pinned input-lending schedule increased declared width to 38. | [Native check](evidence/aggregate34-20261126/invsqrt-prune-native.json) and [input-lending screen](evidence/aggregate34-20261126/invsqrt-lend-pinned.json) |
| DQI | Reset-delimited lifetimes peaked at 900 qubits even when lending measured input wires. Static counts highlight the return, decoder-to-field and field-to-root phase stages for arithmetic work. | [Lifetime screen](evidence/aggregate34-20261126/dqi-reset-lending.json) and [static census](evidence/aggregate34-20261126/dqi-static-census.json) |
| Chemistry | Exact product matching on all 2,438 forward and reverse boundary states per loader emitted identical assembly across all 15 loaders. | [Endpoint screen](evidence/aggregate34-20261126/chemistry-endpoint-screen.json) |
| Chemistry batch size | The pinned verifier recovered every angle word in both banked controls. Four-word batches lowered total width from 405 to 398 qubits. The 19 loaders executed 24,016 Toffolis per pass, compared with 18,960 for banked five-word batches and 3,307 in the publisher's tuned comparison. The banked four-word control priced at 1.018B. | [Native banked control](evidence/aggregate34-20261126/chem-banked-four-word.json) |

The [cloud comparison registration](evidence/aggregate34-20261126/public-cloud-registration.json)
pins the public comparison archive, metric and a development salt. The
registered structural coverage is 200,540,928 inverse-square-root trajectories,
102,400 DQI trajectories and 78,016 chemistry trajectories. This comparison
has a separate verification path from portfolio certification.

Pyright reported zero diagnostics on the changed Python files. The targeted
portfolio, inverse-square-root, chemistry, archive and confirmation tests
passed 29 cases. Strict OpenSpec validation passed.
