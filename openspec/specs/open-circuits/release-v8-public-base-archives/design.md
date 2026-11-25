## Step 1 — member choice (per release)

At registration time, take for each task the preferred member if it is
banked, else the fallback member of the proposal table. Record which of
the two was taken, per task.

A release `v8.N` (N ≥ 1) is made only when a banking event changes at least
one chosen member **and** the new conservative projection exceeds the last
released archive's by at least 2%. Otherwise record `skipped` with both
projections.

`v8.0` has no such condition. It uses the three fallback members.

## Step 2 — upload size limit

1. Read the submission size limit `L` from the competition's submission
   dialog or Rules page. Record the value, where it was read and the date
   in `docs/evidence/v8/upload-limit.json`.
2. If it cannot be read, record `limit: unknown`.

## Step 3 — container mode

Add `compression: Literal["stored", "deflate9"] = "stored"` to the release
packer. `stored` stays byte-identical to today.

`deflate9` uses `ZIP_DEFLATED` at level 9, the fixed member order, the
fixed 1980-01-01 timestamp and no extra fields.

Choice, with both containers built once and both sizes recorded:

| Condition | Mode |
| --- | --- |
| `L` known and stored size ≤ `L` | `stored` |
| `L` known, stored size > `L`, deflate9 size ≤ `L` | `deflate9` |
| `L` known and deflate9 size > `L` | Stop. Record both sizes and `L` |
| `L` unknown | `deflate9` |

## Step 4 — pinned zlib build

1. Pin the zlib build in `configs/release-zlib.json`:
   `zlib.ZLIB_RUNTIME_VERSION`, the Python build identifier, and the
   container image digest or `uv` Python distribution used for packing.
   The first `deflate9` release writes this file.
2. The packer refuses `deflate9` when the running
   `zlib.ZLIB_RUNTIME_VERSION` differs from the pinned value.
3. Member SHA-256 values are the certification key. The container SHA-256
   is valid only together with the pinned zlib build.
4. Test: the pinned metric extracts a `deflate9` archive to the same member
   hashes as the `stored` archive.

## Step 5 — registration (per release)

Write `docs/evidence/v8/v8.N/registration.json` containing:

- the member table with one SHA-256 per member, and `preferred` or
  `fallback` per task;
- the parent archive (v6 `5eb18b89…` for `v8.0`, else the previous release);
- the vendored provenance (`third_party/*/SOURCE.json` hashes) for every
  vendored member;
- the container mode, the upload limit record and the zlib pin;
- one metric salt and one confirmation salt, both fresh;
- the projection band from component receipts:
  - `score_full` uses the DQI zero-failure cost;
  - `score_conservative` uses the DQI pooled price (`dqi-v8`, `dqi-v8m`)
    or the routed conservative price 7,121,637,700,132.021.

## Step 6 — builds, metric, confirmation

1. Two builds in empty directories, with identical member hashes and an
   identical container hash.
2. Preflight. Free memory must be at least 8 GB.
3. Pinned metric once on a fresh extraction with the metric salt, then once
   with the confirmation salt.

| Outcome | Action |
| --- | --- |
| Aggregate within `[score_conservative − 1%, score_full + 1%]` | `go` |
| Aggregate below the band | `no_go`. Record per-task ratios and stop this release. |
| invsqrt or chemistry cost differs from its banked receipt by more than 1×10⁻⁹ relative | `no_go` |

A `no_go` stops only that release. The previous release stays current.

## Step 7 — upload and reconciliation

1. Name the file `submission.zip`, a regular file with no hardlinks.
   Description: `v8.N <12 hex>`.
2. Upload once. Record the public score when it appears.
3. The score is consistent when it lies in the band widened by ±1%. If it
   falls below, record the per-task estimate and the DQI failure count the
   score implies. Do not resubmit in this change.

## Step 8 — attribution

The release notes `docs/v8.N-release-<date>.md` list every vendored member
with its upstream author, URL, revision and licence, plus the root
`LICENSE` and `NOTICE`. The submission ZIP itself contains only the
members the metric expects.
