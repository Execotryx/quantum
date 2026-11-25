Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.

# dfthcsos_source - our chemistry (dfthcsos) submission, rebuilt from source

## What it builds

The 15 ANGLE_k loader circuits `dfthcsos/angle_k_0.kmb` ... `dfthcsos/angle_k_14.kmb` and the
submission file `dfthcsos/submission.npz`.

- The circuits are compiled from source by our own portable compiler (`compiler/`), driven by
  `rebuild.py`, from the frozen loader plans (`plans/angle_k_<k>.json`) and the angle words stored in
  `submission.npz`. No search or optimisation is rerun; the compiler is deterministic.
- `submission.npz` is data: the DF-THC factorization weights (`U`, `W`, `H2_I`, `H1_I`, `Hsym_lower`),
  the `tree_edges` and the 1220 x 75 `angle_words`. It came out of long fitting and search runs and is
  shipped as it is; the build copies it unchanged. `research/` holds the research code behind it
  (not part of the build; see `research/README.md`).

## The single command

```sh
bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR
```

- `ENGINE_DIR`: the competition's `kickmix/` folder (holds the Linux `kickmix.so`, SHA-256
  `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`). The build copies it into its work
  folder beside `rebuild.py`; it is not part of this folder. Another `kickmix.so` only gives a warning; the
  output hash checks decide.
- `VERIFIERS_DIR`: the competition's `verifiers/` folder. Accepted for the common interface; this build
  does not read it (run the official `dfthcsos` verifier on the outputs separately).
- `OUT_DIR`: receives `dfthcsos/angle_k_0..14.kmb` and `dfthcsos/submission.npz`.

Environment variables (all optional on Linux):

- `PY`: the Python command (default `python3`). Must be CPython 3.13 with NumPy. It may be a command
  with arguments (split on spaces), for example `PY="/usr/bin/arch -arm64 /path/to/python3"` on a Mac.
- `WORK`: writable work folder (default: a new folder `${TMPDIR:-/tmp}/dfthcsos.XXXXXX`, removed at the end). The build works
  only in `WORK/dfthcsos_build/`; this folder itself is never written, so it can sit on a read-only disk.
- `PROOF`: `1` (default) also runs our own exact all-branch proof of the 15 loaders (about 2 s, NumPy
  only); `PROOF=0` skips it.
- `MAC_ENGINE` (macOS testing only): a platform-tagged kickmix module such as
  `kickmix.cpython-313-darwin.so`. It is copied beside the Linux `kickmix.so`; Python imports the
  platform-tagged file first.

What the build does: checks the Python, copies this folder into the work folder, checks every file
against `SHA256SUMS` (and that nothing unlisted is present), copies the host `kickmix.so`, runs
`rebuild.py` (which checks each circuit against `manifest.json`), checks all 16 outputs against the
SHA-256 list below, optionally runs the proof, copies the outputs to `OUT_DIR/dfthcsos/` and prints one
line `BUILT <file> <sha256>` per output. Any failure exits non-zero. There are no baked-in absolute
paths: every script finds its inputs relative to its own file.

## Expected SHA-256

| File | Toffolis per call | SHA-256 |
|---|---|---|
| dfthcsos/angle_k_0.kmb | 293 | `ce7ebaf342c5b49f7d539637359fb8a282718fb3057e7b25dd193f2a6a4b8974` |
| dfthcsos/angle_k_1.kmb | 287 | `3eac70665f021b0e304106fd62749277d4d69db775df008aacd6d950e4934193` |
| dfthcsos/angle_k_2.kmb | 287 | `c3e1454e29a05c3c28bcfd16c2aee02340b5d439d9466774424fedf0ed7601d1` |
| dfthcsos/angle_k_3.kmb | 287 | `d26b576ae789b0471ec6c11b7317c7c69eb3d7190472af8120ccf25cf217a8ea` |
| dfthcsos/angle_k_4.kmb | 268 | `2efacc9d944aa5a855acf780e6bbc3c07af16c0275eb9549bb24adc70acca344` |
| dfthcsos/angle_k_5.kmb | 268 | `7e4ed9a363c8f56d85410185c7b4449211788bc61e81b3dc7cbdd10ab7ce8a42` |
| dfthcsos/angle_k_6.kmb | 268 | `26ab1d5df8132bbc28e068a4eef0b247ea21a96fa4034f89a6d1bf306f07e284` |
| dfthcsos/angle_k_7.kmb | 269 | `1ae98642315e7aaedfde99773af4ae48198bf8b4f2e11e97883d6aa1bfe12bee` |
| dfthcsos/angle_k_8.kmb | 263 | `e69c554c360c709e52126a6f773afeaa3564da7be0927d6293665f342203771f` |
| dfthcsos/angle_k_9.kmb | 264 | `38848ce19bd553e4007a454d9b7d392d05ac105cf4b269f41521bd1003bf838e` |
| dfthcsos/angle_k_10.kmb | 264 | `fdb67807154e35d9f41471c22b38bbc3ed07e5c93efef30a57f0599fb8400ff7` |
| dfthcsos/angle_k_11.kmb | 264 | `d22baf8e2d294165618bcee40d958ef2806f0b35352c8b92e0d201aff3269c37` |
| dfthcsos/angle_k_12.kmb | 264 | `b1b6af502f4bf02e521ab888600f645aa5a5bed028290466b54a835423eb2517` |
| dfthcsos/angle_k_13.kmb | 264 | `1843d7993215656e4e0eee69169966ba269d544bc0b90e855e4ed5e6e113accc` |
| dfthcsos/angle_k_14.kmb | 264 | `b763f0cd2fdeaaa31e7811084e51fde5d51575b036fa22854fb28172c1712a8e` |
| dfthcsos/submission.npz | - | `6418ec8e10b1a8da967ee26278434f9ac950474741185f4d61363e17a03da77f` |

ANGLE Toffolis per pass: 4074. Official `dfthcsos` verifier result of this submission when it was made
(our record, not rerun by this build): PASS, score 296635967.5935997 = lambda_eff 46.907347493481 x
Toffoli 14810 x qubits 427.

## Runtime and requirements

Measured on an Apple M5 Mac (arm64, CPython 3.13.7, NumPy 2.2.4 and 2.5.4) while other jobs were running:
about 6 s wall for the whole build including the proof (about 3 s with `PROOF=0`), peak memory about
50 MB. Not measured on Linux; it does the same work there and should take seconds.

Requirements: bash, coreutils, CPython 3.13 with NumPy (no SciPy, no other packages, no network), and
the competition's `kickmix.so`. The build reads only this folder and `ENGINE_DIR/kickmix.so`.

## The ANGLE_k proof and its assumption

With `PROOF=1`, `verification/prove_loader_branches.py` checks every loader exactly on all 1220
addresses, in both directions, for every outcome of every HMR measurement (exact Boolean truth tables
and symbolic phase coefficients). It proves each loader on its two legal endpoints (the words of batch
k-1 and of batch k), which is our reading of the ANGLE_k rule: a loader only has to be correct on the
states it can be reached from. It does not prove behaviour on other input states.

## Folder contents

- `build.sh`, `README.md`, `LICENSE` (Apache-2.0), `NOTICE`, `SHA256SUMS`
- `rebuild.py`, `manifest.json`, `submission.npz`, `compiler/`, `plans/`, `verification/prove_loader_branches.py`:
  the build inputs, byte-identical to our verified package D35
- `research/`: research code only, not used by the build
