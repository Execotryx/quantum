# Corrected exact v6 special-panel preparation

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

The first source version stopped normally with exit 1 before imports or output creation. It incorrectly assumed that the established extra-fixture case ID used the same serialization as the original prepared corpus. Its source, stdout, normal guard and review are preserved. No provider, physical input, native result or original fixture was faulty or changed.

The new sibling `prepare_integration_special_panels_v2.py` strictly binds both original conventions:

| Record | Established case-ID convention | Established case ID |
| --- | --- | --- |
| Existing gauge-one corpus input | Compact sorted JSON of sorted physical error pairs, mask mode and optional mask values, from `prepare_panels.collect` | `54d38bf59904d025bfe626a0db3007111eb8d6c3e975bf0dda3a99d8a4cba57a` |
| Deterministic zero-third extra input | Compact JSON of the ordered `[positions, values]` arrays, from `check_key_boundary.load_cases` | `6663887a36baed1286a39bd8933a2c4d45a0660ef96a6a2b03ea0460588e00b0` |

The second input's standard sorted physical/mask hash is `8359bec906a50537fb2e812301e4cc81a3153c91ee62f1fd4cf83819c8e334a1`. V2 verifies it as a secondary descriptive identity and **does not replace the established case ID**. The unchanged native corpus checker uses the supplied case ID to seed its random masks. Keeping `6663887a...` therefore preserves the existing mask identity as requested.

V2 pins the exact old key harness as well as the original preparer, failed stdout and normal exit-1 guard. The exact once-only source edits, old/new hashes and independent ID mapping are recorded in `SPECIAL_PANELS_V2_DERIVATION.json` and the adjacent unified diff. Every prior physical-data, full classifier, old/new boundary, full783 receipt and normal-guard check remains. The source repair does not relax admission or change the prepared data.

Root's child command, after the new independent source review, is:

```sh
/usr/bin/python3.13 -B controller_work/after_v3/blocks/v6/prepare_integration_special_panels_v2.py --output controller_work/after_v3/blocks/v6/runs/integration-special-panels-v2
```

Run this through the existing blocking shared guard with a fresh output directory. The two separate standard panels will be `gauge1/cases.json` and `raw-zero/cases.json` below that directory. Their individual manifests record the ID convention and secondary hash; the top-level manifest is written only after both preparations complete. The preparer makes no random draw and runs no quantum simulation or official verifier. Full native gauge-one and zero-third panels remain separate integration gates.
