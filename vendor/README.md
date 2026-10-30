# Official dependencies

Keep acquired competition inputs here or in another local directory and inventory
all bytes before use. Do not commit credentials, unpublished data or upstream
assets without checking redistribution permissions.

The public **Google Quantum AI Metric v10** was acquired on 30 October 2026 from:

https://www.kaggle.com/api/v1/kernels/pull/metric/google-quantum-ai-metric

Notebook source SHA-256:
`df418aff0d6eff16ec341da20150255abb49b252256d6abfb253ef8d2643ac73`.

`uv run qcompile assets acquire-metric` retrieves and checks these exact notebook
bytes. The API response metadata is informative; the notebook body controls the
execution pin. The notebook is not redistributed in this repository.

The competition-data listing returned HTTP 401 in the implementation environment.
The actual kickmix binary/source build, verifier package, reference ZIP, numerical
data, starter kit, rules/evaluation snapshots and paper still require acquisition
and reconciliation. See the root README and `contracts/sources.lock.json`.
