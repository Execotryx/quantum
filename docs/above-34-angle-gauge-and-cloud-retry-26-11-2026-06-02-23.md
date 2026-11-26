# Chemistry angle gauge and cloud retry

The ordered Givens tree permits a change in the sine and cosine signs of an
angle while preserving its final prepared vector up to a single sign. The
new encoder walks the tree backward from the desired final signs. At a
quarter turn the parent becomes zero and the child determines the required
input sign. This lets the encoder align cosine markers across four-word
batches on the frozen 1,219 × 75 table. The gauge assigned all markers and
changed 27,162 angle words. The decoded error limits, normalization and gap
passed with the same fitted NPZ bytes. [Gauge evidence](evidence/aggregate34-20261126/chem-angle-gauge-screen.json)

| Local standalone chemistry | Loaders | Total qubits | Toffolis per pass | Verified cost |
|---|---:|---:|---:|---:|
| Published comparison | 15 | 405 | 3,307 | 249,169,842.41 |
| Structured five-word control | 15 | 405 | 3,632 | 261,520,032.86 |
| Structured four-word control | 19 | 398 | 4,469 | 288,256,682.20 |
| Structured four-word gauge | 19 | 398 | 4,400 | 285,679,960.99 |

Each row completed 78,016 trajectories. The gauge recovered 69 loader
Toffolis per pass against the ungauged four-word implementation. The remaining
cost gap to 245M rules out promoting this gate schedule. The structured
controls used the version 2 Apache-2.0 ThemBones compiler from archive SHA-256
`9a66ed2c18c1317ed328ea2ae63da046584619c5eefa98d3c3f5401e52c0cb2b`.
The compiler ran with a four-bit address split, seed 534 and the groups
decomposition. The pinned native verifier recovered the complete word table
and checked forward and reverse boundaries.
[ThemBones compiler source](https://www.kaggle.com/datasets/danishlynxthembones/vqcc-thembones-milestone-generators/versions/2)
[Gauge native receipt](evidence/aggregate34-20261126/chem-angle-gauge-native.json)
[Four-word control](evidence/aggregate34-20261126/chem-structured-four-word.json)
[Five-word control](evidence/aggregate34-20261126/chem-structured-five-word.json)
[Frozen public chemistry](evidence/aggregate34-20261126/public-chemistry-local.json)

Conservative affine-rank replay also reached the full 37-wire span of the
inverse-square-root comparison. The original circuit hash was traced through
Rithvik Redrouthu's version 6 manifest to `d2148a7c…`. That release contains
compiled archives and credits Syed Asad Ali. The separately published Syed
version 17 generator emits a different 43-qubit member, SHA-256
`70fe5f79d56bd48cd8fc9602757a0520b4d11859967627906cccb3dec25b7692`.
The generator for the exact 37-qubit parent remains open.
[Affine rank](evidence/aggregate34-20261126/invsqrt-affine-rank.json)
[Rithvik release](https://www.kaggle.com/datasets/rithvikredrouthu/qcc-milestone-set/versions/6)
[Syed release](https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio/versions/17)

## Cloud storage recovery

The first attempt passed inverse square root at 60,927.60957681 over all
200,540,928 trajectories. The VM boot filesystem had 128 KiB free and native
chemistry serialization failed. The recovered first-attempt tarball hashes
to `77c29eec4b2136e79830386905d835965dce77ab4e6e0c1ac45c0368947ae655`.
The same chemistry circuit serialized byte for byte after privately binding
RAM-backed storage at `/tmp` and running the pinned verifier as the usual
user. The retry uses the original archive, registration and development
salt, with a fresh extraction and its own receipts.
[Failed attempt](evidence/aggregate34-20261126/public-cloud-first-attempt/verification/verification.json)
[Passing component receipt](evidence/aggregate34-20261126/public-cloud-first-attempt/verification/benchmark-invsqrt.json)

Pyright reported zero diagnostics on the gauge and its tests. The focused
unit and regression suite passed eight cases, including exact quarter turns
at three precisions.
