## 1. Reference offsets

- [ ] 1.1 Compute `o_ref = H2_I_ref − W_ref.sum(axis=1)` from the pinned reference NPZ. Record `m_ref`, the mean magnitude and the NPZ SHA-256.
- [ ] 1.2 Compute `B₀` by the rule and record it.

## 2. Settings tool

- [ ] 2.1 Implement `tools/chem_s2_settings.py write` with the binding fields in the design. Validate the output against `chem_s2.py validate_registration`.
- [ ] 2.2 Add tests: the rule's rounding, refusal when any bound hash is missing, and refusal of a second contingency plan.

## 3. Registration

- [ ] 3.1 Write a settings record (values, `B₀`, contingency) before any lane is selected. Record its SHA-256 in the change log.
- [ ] 3.2 After `select-compressed-chemistry-shape` selects a lane, write the bound S2 plan and record its SHA-256.
- [ ] 3.3 Strict OpenSpec validation and a dated change log.
