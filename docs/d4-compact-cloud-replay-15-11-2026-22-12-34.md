# Compact D4 residual error replay

The existing Google Cloud VM replayed both 102,400-shot draws using the
sealed full-grid repair circuit, original salts and pinned verifier
inventory. Both complete verifier dictionaries matched their original
receipts. The diagnostic capture kept the exact RNG and simulator seeds
and nearby passing inputs. The downloaded archive matched SHA-256
`47c3b0741358c3687eab21bebd0dcd09fd087693fa54acd3514c1d2104ab0cfa`.
The VM was confirmed terminated after collection.

| Draw and shot | Weight | Scalar chart | Full-grid result | Banked result | Homogeneous groups 1–7 |
| --- | ---: | --- | --- | --- | --- |
| s6 / 102316 | 32 | First-head pole at head 12 | q840 dirty, raw phase wrong | Phase error | Clean |
| s7 / 52983 | 33 | First-head pole at head 4 | q840 dirty, raw phase correct | Clean | Clean |

Each complete captured batch had 256 shots. All three exact circuit
hashes were checked before the matched replay. Both full-grid shots
restored syndrome and masks and left only q840, the rational rejection
flag, dirty. The repeated-root counter stayed clean. Official phase
counts exclude value-error shots.

The separate native extraction and synthesis probe agreed with all
24 and 8 scalar head words before the two incoming poles. At those
boundaries it continued with head pairs `(0,0),(3635,3573)` and
`(0,0),(95,745)`, respectively, with every second-head chart flag
false. It reconstructed degree-(34,35) polynomials in both cases,
which failed the original moment congruence. Both neighboring controls
passed the same check. This reproduces the first unsupported chart
and the later rejection separately from the sealed full verifier run.

The homogeneous control preserved the required phase and cleanup on
all 512 shots. Carry these cases into the compact fold integration as
first-head pole regressions, distinct from the captured second-head pole
and the ordinary intermediate jets.

[Matched replay](evidence/d4-compact-repair-20261115/matched-residual.json)
· [Native boundary probe](evidence/d4-compact-repair-20261115/native-probe.json)
· [Cloud captures and receipts](evidence/d4-compact-repair-20261115/cloud-replay/captures/)
· [VM stop](evidence/d4-compact-repair-20261115/cloud-replay/vm-stop.json)
