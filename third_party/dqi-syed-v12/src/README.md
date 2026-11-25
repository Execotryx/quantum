# DQI circuit generator (dqi.kmb)

Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.

## What it builds

This folder rebuilds our DQI decoder circuit `dqi.kmb` from source:

| File | Bytes | SHA-256 |
|---|---|---|
| `dqi.kmb` | 455,590,024 | `7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9` |

The generator itself asserts Q = 889 qubits and 384,003 static Toffoli-like gates
before it writes the file. The build is deterministic: the same bytes every time.

## The single command

```
PY=python3.13 bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR
```

- `ENGINE_DIR`: the competition's `kickmix/` folder (holds the Linux `kickmix.so`).
- `VERIFIERS_DIR`: the competition's `verifiers/` folder (holds `dqi/verify_submission_dqi.py`).
- `OUT_DIR`: where `dqi.kmb` is written.

It prints `BUILT dqi.kmb <sha256>` and exits non-zero on any failure, including a
hash that differs from the table above.

Optional environment variables: `PY` (Python to use, default `python3`), `WORK`
(writable scratch folder, default a new temporary folder), `KEEP_WORK=1` (keep the
copied source tree after success).

## Requirements

- Linux x86_64 with CPython 3.13 and numpy. No other package, no internet, no pip install.
- Ordinary Python: do not use `-O`. build.sh unsets `PYTHONOPTIMIZE`.
- Memory: peak about 1.0 GB resident (measured on macOS). The generator's own memory guard
  refuses to start with less than 4 GB available and stops the build at 4 GB.
- Disk: about 0.5 GB in `WORK` and `OUT_DIR`. The guard also uses the lock file
  `/tmp/syed_dqi_heavy_job.lock`, so `/tmp` must be writable.
- Runtime: about 3 minutes (measured 190 s on an Apple M5 for the macOS test; Linux not timed here).
- Tested with numpy 2.2.4 (the original Linux builds also used numpy 2.2.4).

The source folder may be read-only (for example under `/kaggle/input`): build.sh
copies it into `WORK` first.

## What build.sh does

1. Checks Python (CPython 3.13, not optimized, numpy importable).
2. Copies `src/` into a new folder under `WORK`.
3. Copies the two host files the pinned sources expect, and checks their SHA-256:
   - `ENGINE_DIR/kickmix.so` to `pro1_controller_bundle/1_task/official/kickmix.so`
     (`c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`);
   - `VERIFIERS_DIR/dqi/verify_submission_dqi.py` to
     `pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py`
     (`f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65`).
   These host files are not part of this folder.
4. On Linux runs the package's entry point
   `controller_work/after_v3/integration_v7/gen_dqi.py`, which starts its memory guard
   (`controller_work/after_c5/root/guard_wait.py`) and the builder (`build_v7.py`).
5. Checks the SHA-256 and size, moves `dqi.kmb` to `OUT_DIR`.

No absolute path needs relocating: every path the sources use is relative to the
copied tree.

## Folder contents

- `build.sh`, `README.md`, `LICENSE`, `NOTICE`, `SHA256SUMS`.
- `macos_launch.py`: used only for a macOS test (see below); Linux never uses it.
- `src/`: 425 files. These are exactly the files the generator opens during a build
  (found by tracing every file opened in a full build). Most JSON and Markdown files
  under `src/` are hash-pinned records (source manifests, component-gate reports,
  source reviews) that the generator checks before it builds: it refuses to build if
  any of them is missing or changed. Folder names such as `pro1_controller_bundle`
  are kept because the pinned sources name those paths.

Imports outside the standard library: `numpy` and the host engine `kickmix`.

## macOS test (not needed on Linux)

The memory guard reads `/proc`, which macOS lacks, and the host engine is a Linux
binary. On macOS, set `MAC_ENGINE` to a macOS build of the engine
(`kickmix.cpython-313-darwin.so`). build.sh copies it beside the Linux `kickmix.so`
and starts `build_v7.py` through `macos_launch.py`, which points the engine module's
file name at the Linux `kickmix.so` so that the source inventory written after the
circuit sees the official engine hash. The circuit bytes are the same as on Linux.
