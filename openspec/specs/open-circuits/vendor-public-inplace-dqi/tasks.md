## 1. Admission

- [x] 1.1 Record origin, authors, revision, licence and the origin's published hash where verified. Record each available hint comparison and the missing evidence for excluded candidates.
- [x] 1.2 Apply the admission and denylist checks. Vendor the admitted D4 and D5 sources.

## 2. Regeneration

- [x] 2.1 Add the vendored-DQI adapter with pinned Python and kickmix.
- [x] 2.2 Build each admitted candidate twice. Require identical hashes, and equality with the origin's published hash where one exists.
- [x] 2.3 Record `Q`, Toffoli counts, size, wall time and peak RSS.

## 3. Pricing

- [x] 3.1 Implement the pooled price of Step 3 with a unit test on the four worked examples.
- [x] 3.2 Register 8 fresh salts for the frozen D4 and D5 field.
- [x] 3.3 Stage 1: every candidate on `s1` and `s2`. Rank by `S = 2` pooled price.
- [x] 3.4 Stage 2: the top two on `s3 … s8`. Compute `S = 8` pooled prices.

## 4. Selection

- [x] 4.1 Apply the selection rule and outcome table. Bank `dqi-v8` or record `no_go`.
- [x] 4.2 `NOTICE` and `README.md` credits. Dated change log. Strict OpenSpec validation.
