# invsqrt source: rebuild of `invsqrt.kmb`

Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0 (see `LICENSE` and `NOTICE`).

## What it builds

This folder rebuilds our circuit for the competition's **invsqrt** task, `invsqrt.kmb`, from our own generator
sources. The build is deterministic. The expected output is:

| File | SHA-256 |
|---|---|
| `invsqrt.kmb` | `321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177` |

The circuit works at Q = 46. Its exact gate expectation is 1511.5703125 Toffoli-like gates, 1 T gate and
33 generic rotations (computed by the generator, not sampled).

## The single command

```bash
bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR
```

- `ENGINE_DIR`: the competition's `kickmix/` folder. It holds the Linux `kickmix.so`
  (SHA-256 `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`).
- `VERIFIERS_DIR`: the competition's `verifiers/` folder. It holds `invsqrt/verify_submission_invsqrt.py`
  (SHA-256 `ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a`).
- `OUT_DIR`: the folder where `invsqrt.kmb` is written.

On success the last line is `BUILT invsqrt.kmb 321aff83...`. Any failure exits non-zero.

Optional environment variables:
- `PY`: the Python to use (default `python3`).
- `MG`: a command prefix for the heavy steps, for example a memory guard (default: empty).
- `WORK`: a writable folder (default `${TMPDIR:-/tmp}`). The build makes a fresh subfolder `invsqrt_build.XXXXXX`
  in it for the work tree and logs. The source folder itself is only read, so it may sit on a read-only disk.
- `MAC_ENGINE` (macOS only): a macOS build of the kickmix extension (`kickmix.cpython-313-darwin.so`). It is placed
  beside the Linux `kickmix.so`; Python loads the platform-tagged file first, and the sources still check the hash of
  the Linux file.

Kaggle example (no internet needed):

```bash
PY=python3 WORK=/tmp bash build.sh /kaggle/input/<competition>/kickmix /kaggle/input/<competition>/verifiers /kaggle/working/out
```

## Requirements

- Linux x86_64 (Kaggle) or macOS, with bash and the usual core tools (`cp`, `awk`, `grep`, `mktemp`).
- CPython 3.13 with numpy. The build uses only the Python standard library, numpy and the competition's kickmix
  engine. It does no SAT solving, no network access and no package installs.
- The competition's host files (`kickmix.so` and the official verifier). They are **not** included here. `build.sh`
  copies them from `ENGINE_DIR` and `VERIFIERS_DIR` into the work tree where our pinned sources expect them, and the
  sources check their SHA-256.
- About 0.6 GB of memory (peak of the largest single step, measured on the Mac) and about 35 MB of disk for the
  work tree.

## Runtime

On an Apple M5 (native arm64, Python 3.13.7, numpy 2.2.4) the full build takes about 80 s of wall time (measured).
Linux x86_64 timing has not been measured here; expect the same order of minutes.

## What the build does

1. Copies `src/` into a writable work tree. It copies the host files into `work/c10/narrow/base/official/`. Then it
   replaces the placeholder `@FG_ROOT@` in the `.py`/`.sh` files outside `work/c10` with the work tree path.
2. `tools/build_variant.py` loads the frozen, hash-pinned base generator (`work/c10/`) and applies the 13 patch
   modules listed in `patches/PATCH_ORDER.txt`. Each patch replaces functions on the live module objects, so no
   pinned source file is edited and every hash check in the frozen sources still runs.
3. `tools/pipeline.sh` runs the mechanical passes on the circuit text. Each pass is driven by a full-domain scan of all
   3,133,452 inputs: held AND products, affine Toffoli-like gates rewritten, and merged Z-power gates. The pipeline then
   compiles the circuit and runs the exact full-domain proof (`tools/prove_any.py`).
4. `agents/composer/post_inplace.sh` applies the declared post pass (`agents/micro47/scripts/relocate_cs2.py`). It then
   compiles again and runs the exact proof again. The proof must report
   `PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS`.
5. Checks the SHA-256 of the result and writes `OUT_DIR/invsqrt.kmb`.

The logs `build.log`, `pipeline.log` and `post.log` are written to the work folder; its path is printed at the end.

## Contents

- `build.sh`: the build script.
- `src/`: the generator tree, holding only the files the build reads.
  - `src/work/c10/`: the frozen base generator.
  - `src/tools/`, `src/patches/`, `src/agents/`, `src/work/pro1_013/`, `src/work/pro2_q47_loader/`: the patch
    layer, its data and its tools.
  - `src/tools/env.sh`: a small file written for this release.
  - Most files under `src/` are pinned by SHA-256 from other files, so they are kept byte for byte as they were
    built. One exception: in three certificate JSON files (`agents/composer/p/v9_form_e2.json`,
    `agents/loader2/certs/first_cap20_56b8.json`, `agents/loader2/certs/second_cap19_70nb1.json`) the build
    machine's absolute provenance paths were made relative for this release, and the SHA-256 pins that check them
    were updated in the three patch files that load them. The build never opens those paths; the rebuilt circuit is
    byte-identical.
- `SHA256SUMS`: the SHA-256 of every file in this folder.
