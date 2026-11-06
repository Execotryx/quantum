# Steps 1–3 on Google Compute Engine

Created 06-11-2026-15-42-50 in Asia/Qyzylorda.

The x86-64 `e2-highmem-2` worker completed all three steps under CPython
3.13.14 with frozen dependencies. The isolated deployment ran revision
`e4241dc49369e55f02eb2c54f5a68a82f4eca293`. The deployment-specific contract
pins the relocated backend inventory. The original local evidence was retained.

- **Step 1 passed.** All 34 extracted files matched the original archive. The
  contract returned ready with zero blockers and hash
  `1c69f5c3ac95c9f602c817b24e01803b1fbd7d2d39b7344298aabdfc01e0e2b5`.
- **Step 2 passed.** A1, A2 and B1 ran serially at full strength in 2,130.86,
  2,056.44 and 2,053.12 seconds. A1 and A2 had identical costs. The largest
  sampled process-tree PSS was 9,753,849,856 bytes with zero sampled swap.
  This is a sampled peak and can miss short events. The measured planning
  memory reserve with headroom was 12,192,312,320 bytes.
- **Step 3 passed.** All 291 tests passed with zero failures, errors or skips.
  The independent validation archive records G0 and G1 as passed.

The snapshot's fixed input list omitted two supplementary files. The bootstrap
added the pinned starter-kit file. The first VM contract check caught the
missing metadata file. The retry added its exact pinned bytes and passed
Step 1 before the baseline campaign began.

The two-hour VM stop limit interrupted Step 3 after the completed baseline
archive had been verified. On the same VM, the recovery checked that archive
before rerunning Step 3. The first recovery hit a recovered-word overwrite
guard. Its logs and the earlier chemistry artifact were preserved before the
successful retry. The VM was then stopped with its original 3,600-second limit.

The final validation artifacts were uploaded to the configured private bucket.
The downloaded receipt archive matched the SHA-256 recorded on the VM. Local
raw receipts and JUnit output are under `runs/cloud-vm-results-20261106/`.

| Artifact | Members | SHA-256 |
| --- | ---: | --- |
| Baseline archive | 91 | `20567d431f7fff0bbef444993a8a445c963b55c5ca4333bfda6cefd5b7b0bff3` |
| Independent validation archive | 29 | `fa6737e9a9ab8ed7d873eea7cc15cac70571aef899e2c4d631ac9d83e2a5b5d6` |
| Validation receipts | | `73e08b8f0939bc77d74f5d6c1ecf506820cebad0e365839ebc24d7da8f5c413c` |

The simplest recovery was to keep the original verifiers, tests, and frozen
baseline, and rerun only Step 3. This avoided repeating over 104 minutes of
full-strength baseline runs. Both orchestration scripts passed Pyright before
execution.
