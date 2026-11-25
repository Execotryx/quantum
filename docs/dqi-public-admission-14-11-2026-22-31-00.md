# Public in-place DQI source admission

Q880 was admitted from the author's dataset version 5. The 151 retained
source files match the origin's manifest. The project additionally pins
the origin's manifest, license, and DQI notice. Two author-published
records bind the expected circuit to SHA-256
`e8083195cec294f2adde9f1b991bcc348233f549a49e5083ac25a12d0777385b`.
The J-fraction build and its dependencies were inspected for the disallowed
Schur source and 891-qubit binary. Four official competition files in the
origin's lab directory were excluded.
[Q880 origin](https://www.kaggle.com/datasets/mrmeows/qcc-1375-open-circuits/versions/5)

The upstream entry point is `third_party/dqi-d5/src/build.py` with
`--output <fresh-directory>/dqi.kmb`. Use Linux x86-64 with Python 3.13
and resolve `vendor/official/kickmix` and `vendor/official/verifiers/dqi`
through `PYTHONPATH`. The origin pins NumPy 2.5.4. The output must match
the origin hash in both clean builds before proceeding to the verifier.

D4 was admitted from the original SomeJoint setup cell preserved in a
versioned reproduction notebook. All 79 retained DQI sources and plans
match the embedded manifest. The author's builder pins SHA-256
`53d8b2edf251e2a0c54c401a97d1396c7ed309e1cbfaab8d54a2c99a11ed6552`,
which differs from the OpenSpec hint. The builder uses bundled source and
separately installed Kickmix. Its original attribution records earlier
Schur design lineage, and its build inputs contain the authored streamed
decoder. [Versioned D4 mirror](https://www.kaggle.com/code/cosmorin/quantum-somejoint-22-75-guard-verified)

D2 has a complete hash-checked source bundle and a pinned expected KMB.
The pinned dataset version declares mixed terms and limits the scope of
its supplied license to the inherited source kit. The adapted helper and
wrapper lack an explicit license at that revision, so D2 and its
dependent D3 are excluded. The Özer variant is excluded because the
named patch could not be tied to a source release and a pinned Q880
parent. Stage one has two admitted candidates, D4 and D5.
[Admission record](evidence/vendored-dqi/admission-20261114.json)

All three vendoring integrity tests passed. Pyright reported 536
diagnostics on the upstream Q880 files and 934 on the upstream D4 files,
including standalone import resolution and upstream type diagnostics.
The upstream files retain their original hashes.
