# Exact v6 physical panels for integration

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

`prepare_integration_special_panels.py` is a new source-only preparer. It writes two individually named standard `C27_PHYSICAL_PANEL_V1` packages, each with exactly one existing physical input and the original canonical mask identity. It performs no draws and does not call the corpus collector.

The `gauge1` panel is the existing weight-18 `M128_all_raw_boundaries:88` case, canonical ID `54d38bf59904d025bfe626a0db3007111eb8d6c3e975bf0dda3a99d8a4cba57a`. The new third-chart carry is `(0, 2229)`; this exact input passed the 783-case key panel.

The `raw-zero` panel is the existing deterministic weight-16 zero-third-residue construction, canonical ID `6663887a36baed1286a39bd8933a2c4d45a0660ef96a6a2b03ea0460588e00b0`. The raw residue and repaired middle are both zero, while the original admitted queried numerator and denominator remain units. This input also passed the complete key panel.

Before writing, the preparer pins the completed full-key report, fixtures, normal guard, original prepared corpus, zero-case package, zero-preparation report/guard, unchanged classifier and scalar boundary helpers. It checks the exact physical values, canonical IDs, original random mask mode, full classifier admission, and the complete old/new scalar boundary equality. Existing origin annotations are preserved. No old source, fixture or native receipt is changed. A standard prepared package does not itself establish new native or full-decoder validation.

Root may run the following child through the shared blocking guard, using a fresh output directory. The preparer is intended as a small classical job; the separate native key/full-decoder gates remain root-owned.

```sh
/usr/bin/python3.13 -B controller_work/after_v3/blocks/v6/prepare_integration_special_panels.py --output controller_work/after_v3/blocks/v6/runs/integration-special-panels
```

Outputs expected after a normal guarded preparation are:

- `runs/integration-special-panels/gauge1/cases.json` and its preparation manifest;
- `runs/integration-special-panels/raw-zero/cases.json` and its preparation manifest;
- `runs/integration-special-panels/manifest.json`, written only after both panels are complete.

All paths above are relative to `controller_work/after_v3/blocks/v6/`. Native checkers should consume these exact `cases.json` files through their standard fixture-path API. The physical prefix/key oracle must use the independently replayed third-chart boundary, and a full-decoder test must retain its original physical phase oracle. Neither panel replaces the original 783-case component coverage, old 76 exclusions, full physical corpus, or official four-salt gates.
