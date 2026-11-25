# V6 special-panel preparer v2: corrected identity review

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**Conclusion:** the new sibling correctly distinguishes the two established input-ID encodings and preserves the actual physical records and mask-seed identities. It is ready for root's guarded classical preparation. No classifier, boundary oracle, preparer, sampler or native job was run in this review.

| Reviewed file, relative to `controller_work/after_v3` | SHA-256 |
|---|---|
| `blocks/v6/prepare_integration_special_panels_v2.py` |`13dded8cccb5f46faf94973e20c74f6f7a6c587d9b529ef0d1effa9e4f8fc602`|
| `blocks/v6/INTEGRATION_SPECIAL_PANELS_V2.md` |`f8a3ef3d448b5625c8d14aae9319b3e1a87ebc79c7158e9d043cc103e9a07df4`|
| `blocks/v6/SPECIAL_PANELS_V2_DERIVATION.json` |`3e991af19424de4df2a6d990d61026a0115b81b4a1859479d463aa4fec94a8ae`|

## Preserved failure and correction

The first preparer, SHA `29c9c8dda21774d236caa2f06bc5ddc380cc3bfe9c6e5532489d586537101528`, failed before imports and output creation when it asserted that the extra-case ID used the standard prepared-corpus encoding. Its normal exit-1 guard is `33e76c120c3220a1429d8bf36f90afecc0cb5795d63f6d0ac56f9e48bcd3aa4b`; its stdout is `fb8470cc85927415294fecebd71c2477c62062bb8c19f5e96780d3221857beb6`. Those files and the earlier source-only review are retained unchanged. The earlier review's unqualified canonical-ID statement was incomplete: it did not distinguish the extra-loader serialization. This new review corrects that conclusion.

The immutable `check_key_boundary.load_cases` extra-fixture path hashes compact JSON of the **ordered** `[positions, values]` lists. The standard `prepare_panels.collect` path hashes sorted error pairs together with mask mode and optional mask values. Both are valid established identities, but they differ for the constructed raw-zero input.

The recorded raw-zero ID remains `6663887a36baed1286a39bd8933a2c4d45a0660ef96a6a2b03ea0460588e00b0`. Its standard physical/mask hash is separately recorded as `8359bec906a50537fb2e812301e4cc81a3153c91ee62f1fd4cf83819c8e334a1`. V2 verifies both and does not replace the recorded ID. The unchanged corpus checker accepts that recorded ID and uses it in its mask-seed derivation. Preserving it is therefore required for the requested mask identity.

The actual gauge-one input remains the original standard-corpus ID `54d38bf59904d025bfe626a0db3007111eb8d6c3e975bf0dda3a99d8a4cba57a`. Its physical and mask encoding does not change.

## Bounded source checks performed

All18 pinned source/evidence files were rehashed. The nine declared once-only replacements exactly regenerate v2 from the preserved first version. Only the two pure JSON/hash identity helpers were evaluated, on the two already recorded inputs. Their results reproduce both established IDs and the descriptive secondary hash. The label, positions, magnitudes, roots, weight, mask mode and syndromes match the pinned prior records exactly for each case.

The complete classifier admission, old/new scalar boundary equalities, full783 native receipt binding, fresh output restriction, source rehash before write, two separate standard packages and final master-manifest ordering are unchanged. V2 adds the exact old extra-loader and failed-attempt evidence as pins. No physical input, accepted provider, source admission, mask mode or native check is weakened.

Root's new preparation must use the fresh `runs/integration-special-panels-v2` output. The resulting packages and their normal guard must subsequently be hash-bound by the joined workflow. Preparation remains separate from all eight required joined test roles, including the complete4095-position raw-zero phase/restoration gate.
