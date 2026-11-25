# V6 special physical panels: source review

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**Conclusion:** the preparer preserves the two exact physical inputs already present in the completed 783-case third-chart key panel. It is suitable for root to run as a bounded classical preparation step. This review does not run the preparer, classifier, boundary oracle, sampler, or native checker and does not establish a joined-decoder result.

Reviewed files:

| File | SHA-256 |
|---|---|
| `blocks/v6/prepare_integration_special_panels.py` | `29c9c8dda21774d236caa2f06bc5ddc380cc3bfe9c6e5532489d586537101528` |
| `blocks/v6/INTEGRATION_SPECIAL_PANELS.md` | `dca94719324a4db16bf5edbbfd4d33be5fab6aa708732292ccda16149b3f79c4` |

Paths in this table are relative to `controller_work/after_v3`.

The gauge-one panel identifies case `54d38bf59904d025bfe626a0db3007111eb8d6c3e975bf0dda3a99d8a4cba57a` by its actual third-chart boundary: weight18, carry `(0,2229)`, selected coordinate2229, and zero other coordinate. It also requires that this is the exact old prepared-corpus physical row. Thus an earlier gauge label is not used as evidence for the new chart.

The raw-zero panel identifies case `6663887a36baed1286a39bd8933a2c4d45a0660ef96a6a2b03ea0460588e00b0`: weight16, raw third residue zero, repaired middle zero, and nonzero queried numerator and denominator. Its complete old classifier admission and old/new boundary values are rechecked against the pinned deterministic construction. No probability claim follows from that construction.

The source pins the completed 783-case report, its exact fixture bytes and normal guard, the zero construction and its guard, the unchanged physical preparation/classification/oracle helpers, and the original prepared corpus. Its canonical-ID calculation matches the original convention: sorted physical error pairs for random masks, with mask mode and optional mask values included in the hash. The code retains the original positions, magnitudes, syndromes, roots, labels and random-mask identity; it draws no masks. The unchanged native checker will supply masks under its existing seed rules.

Both standard `C27_PHYSICAL_PANEL_V1` packages are prepared from validated rows before the output directory is created. The output must be a fresh descendant of the designated `blocks/v6/runs` directory. Existing input bytes are rehashed before writing. The master manifest is written only after both named one-case packages and their manifests exist. It labels native execution, full-decoder checking and population claims false.

The joined release workflow must retain the original regression inputs and consume these newly prepared packages through the existing fixture API. In particular the raw-zero case still needs a complete4095-position native phase/restoration check, and the actual gauge-one case must be observed under the new boundary oracle. Those gates are separate from this source review and from the already completed component key test.
