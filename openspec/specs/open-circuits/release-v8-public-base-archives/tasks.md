## 1. Packer and limit

- [x] 1.1 Record the upload size limit, or `limit: unknown`.
- [x] 1.2 Add the `deflate9` container mode. Prove that `stored` output is byte-identical to today's.
- [x] 1.3 Add the zlib pin file and the packer's refusal on a mismatch.
- [x] 1.4 Compare the member hashes from both container modes and pass the DEFLATE extraction to the pinned metric readers.

## 2. Release v8.0 (fallback members)

- [x] 2.1 Register v8.0 with v6 invsqrt, routed DQI `d41de9ee…` and v6 chemistry, salts and band (2.6154 to 2.6228).
- [x] 2.2 Apply the container choice. Build twice and run the preflight.
- [x] 2.3 Run the metric and the confirmation. Apply the outcome table.
- [ ] 2.4 Upload `submission.zip` once and reconcile. Write the release notes.

## 3. Releases v8.N

- [ ] 3.1 After each banking event (`chemistry-v8`, `dqi-v8`, `invsqrt-v8`, `dqi-v8m`), apply the member choice and the 2% rule.
- [ ] 3.2 If not skipped, repeat 2.1–2.4 for the new member table, with attribution in the release notes.

## 4. Records

- [x] 4.1 Dated change log and strict OpenSpec validation.
