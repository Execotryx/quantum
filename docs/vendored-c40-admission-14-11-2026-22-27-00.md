# Public chemistry source admission

Both specified pairings were recorded as hash references. Neither reached
regeneration. The v6 chemistry family remains the fallback.

- **P1.** Lera’s version 7 compact-pipeline dataset includes an Apache-2.0
  license, the C40 training code at revision
  `704091bf1e1325b090202343e4d8130ff1c80b64` and the open-pattern C40
  checkpoint. All seven arrays match Lera’s original notebook v9 export,
  SHA-256 `2601de78…`. The spec hint `89357442` matches another
  publication, kawh1111’s portfolio v2, with the same angle words and
  different numerical weights and identity offsets. Under the source
  policy, the source origin’s hash governs a future rebuild. Wahyu
  Rahmaniar’s originating `plan.py` and `loader.py` revision could not
  be established. The Kaggle CLI returned no author notebooks for both
  the competition-filtered and unfiltered lookups.
  [Lera’s versioned dataset](https://www.kaggle.com/datasets/marculera/dfthc-compact-pipeline/versions/7)
  · [First observed reference](https://www.kaggle.com/code/kawh1111/qcomp-harvest-v32)
- **P2.** EigenOS v7 assembles already generated assets. The published
  weights reference attributed to Kaliden Aiarys hashes to `b463690f…`.
  The spec’s `b93b4db795e7` is the ledger family identifier. The weights
  origin returned HTTP 404 through both the public source endpoint and
  the configured Kaggle CLI. Aiarys’s later public notebook copies a
  prebuilt ZIP.
  The loader origin, qwertykeypadapple, separately publishes the build
  driver and all 15 plans and declares those files Apache-2.0. The
  admission record preserves the individual loader hashes.
  [Pinned EigenOS notice](https://github.com/EigenOS-Quantum/eigenos-vqcc/blob/f4dd22d26a31b23a24db25ef461ddff4efcc3f85/NOTICE-v7.md)
  · [Loader source](https://www.kaggle.com/datasets/qwertykeypadapple/qcc-kernel-search-portfolio/versions/1)

[Admission record](evidence/vendored-chemistry/admission-20261114.json)
