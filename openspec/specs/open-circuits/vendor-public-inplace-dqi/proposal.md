## Why

DQI cost is `R(ε⁺)·Q²·T`. Our routed decoder uses 1,942 qubits. Public
in-place decoders keep the 840 syndrome qubits plus about 50 working qubits.
On `Q²` alone that is a 4.3–4.75× advantage.

| ID | Source (hash prefixes are hints, policy 5.1) | Licence | Q | Mean Toffoli | Ratio | Generating source |
| --- | --- | --- | ---: | ---: | ---: | --- |
| D2 | ahoirg "QCC Reproducible Circuit Assets" v1 (SomeJoint / yoyobar lineage), output `fb2da4f2…` | Apache-2.0, per wahyurahmaniar CREDITS | 893 | 407,444.1 | 63.141 | `build_dqi.py` (`80c39449…`), `dqi-source-bundle.json` (`a7f22360…`) |
| D3 | wahyurahmaniar patch set `c453c7ac` on D2 | Apache-2.0 | 892 | 407,005.2 | 63.351 | patch plus D2 |
| D5 | mrmeows Q880 source release, optionally with Özer's `merged_own_shared` patch (−26,424 Toffoli) | Apache-2.0 with LICENSE and NOTICE | 880 | not published | — | yes |
| D4 | SomeJoint 897-qubit `c300b06e` (`build.py`, 53 modules) | Apache-2.0 | 897 | — | 59.18 | yes |

Expected DQI ratio is about 63. That multiplies the aggregate by about 2.6
compared with v7.

## What Changes

- Admit, vendor and regenerate the candidates D2, D3, D5, D5 with the Özer
  patch, and D4. No other candidates.
- Price in two stages on 8 registered salts: all candidates on 2 salts,
  then the best two on the remaining 6.
- Price from the pooled failure rate over the salts a candidate has run,
  not from its worst salt.
- Bank the selected decoder as `dqi-v8`.

## Impact

- Requires `adopt-vendored-source-policy`.
- Pauses the routed-decoder roadmap. Our routed decoder stays the DQI
  fallback member until `dqi-v8` is banked.
- Build ≈ 4 min and 2.5–3 GB RAM. Official verification can peak near
  7.6 GB, so the worker needs at least 16 GB RAM.
- The KMB is about 530 MB.
- Full-coverage runs: at most 2 × 5 + 6 × 2 = 22, down from 40.
