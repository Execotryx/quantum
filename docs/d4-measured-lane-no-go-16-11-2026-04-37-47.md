# D4 measured lane disposition

Retain the banked 897-qubit D4 component for the variants evaluated
under this change. Its serialized SHA-256 is
`53d8b2edf251e2a0c54c401a97d1396c7ed309e1cbfaab8d54a2c99a11ed6552`.
The selected v8 member record and the local artifact agree with this
identity. The recorded D4 repair comparison provides the pricing
reference for this decision. It uses separate draws from the v8
member selection.

## Official historical comparison

The archived comparison contains eight 102,400-shot receipts for
each role. All passed. The banked run had zero observed value and
phase errors. The 4,081-qubit full-grid repair had two value errors
and zero phase errors. Its pooled price was 63,747,071,243,053.88,
against 414,840,001,725.70 for the banked control.
The official roles share their salts, and the verifier derives
each shot stream from the circuit hash.

Same-input replays attribute both repair value errors to the
verifier-visible rational rejection at wire 840. The first-head
pole charts occur at head 12 on s6 and head 4 on s7. The banked
decoder reported a phase error on the s6 input of that matched
replay. The 904-qubit homogeneous control cleared both residual
inputs, but the historical s2 shot 45440 still had a phase error.

[Official registration and draw identities](evidence/d4-extraction-repair-20261115/full-cloud-registration.json) ·
[Banked pooled receipts](evidence/d4-extraction-repair-20261115/full-cloud/campaign/banked/summary.json) ·
[Full-grid pooled receipts](evidence/d4-extraction-repair-20261115/full-cloud/campaign/candidate/summary.json) ·
[Residual same-input replay](evidence/d4-compact-repair-20261115/matched-residual.json)

## Archived compact price screen

The preflight ceiling at declared width q is the historical banked
price divided by q² and by the minimum eight-draw repetition
factor, 1.1967314991687559. Each row uses the largest executed
mean from its own measured fixture scope.

| Lane | Qubits | Observed gates | Ceiling | Above ceiling |
| --- | ---: | ---: | ---: | ---: |
| Homogeneous groups 1–7 | 904 | 430,148.56 | 424,176.93 | 5,971.63 |
| Fixed degree-31 chart | 920 | 415,535.50 | 409,551.24 | 5,984.26 |
| Live degree-31 route | 926 | 421,805.17 | 404,261.08 | 17,544.09 |
| Incoming pole s6 route | 939 | 433,854.00 | 393,144.97 | 40,709.03 |
| Incoming pole s7 route | 940 | 443,792.75 | 392,308.93 | 51,483.82 |
| Fused shared captured-input route | 970 | 468,588.54 | 368,417.66 | 100,170.88 |
| Shared regular full-weight route | 1,039 | 491,617.76 | 321,109.25 | 170,508.52 |
| Shared full-weight route with rejection wire | 1,011 | 495,129.18 | 339,142.01 | 155,987.16 |

These observations decide the preflight gate for the measured
variants. The compact rows are native development receipts over
different fixture scopes. The last variant has verifier-visible
rejection for the unsupported mixed weight-35 witness. Its measured
gate count would require a width of at most 836 qubits to beat
the historical price, fewer than the 840 syndrome wires.

The earlier full-grid and pooled leading-band approaches
also missed their respective priced gates. The fixed-degree and
separate-pole routes have narrower coverage. The shared route
improves supported coverage, and still needs exact mixed full-weight
decoding and substantial reductions in both width and executed gates.

[Hash-bound audit](evidence/d4-compact-repair-20261115/measured-lane-no-go.json) ·
[Banked v8 member record](evidence/vendored-dqi/dqi-v8.json) ·
[Pooled leading-band resource result](d4-pooled-aligned-replay-16-11-2026-00-53-42.md)

## Current-source compact rescreen

The archived degree-31 and incoming-pole fixtures predate the
collapse arithmetic fusion. The rescreen reruns the same
fixtures on the current source. The fixed degree-31 probe now
clears its numeric gate on the captured chart. It assumes the
chart and synthesized degree at circuit construction, so it
has no matched-batch qualification. The guarded degree-31
variant applies its residual phase only when the live checks
pass and restores the rejected controls. That variant is still
5,670 gates per shot above its price ceiling.

| Current-source lane | Qubits | Observed gates | Ceiling | Margin |
| --- | ---: | ---: | ---: | ---: |
| Fixed degree-31 chart | 920 | 403,506.50 | 409,551.24 | 6,044.74 below |
| Live degree-31 route | 926 | 409,931.00 | 404,261.08 | 5,669.92 above |
| Incoming pole s6 route | 939 | 422,378.50 | 393,144.97 | 29,233.53 above |
| Incoming pole s7 route | 940 | 431,991.75 | 392,308.93 | 39,682.82 above |

At its measured gate count the live degree-31 variant could
use at most 919 qubits. Its extraction alone has already
introduced 920 declared qubits. The rescreen leaves the
selection decision unchanged. Each incoming-pole variant
has a separate fixed layout and also exceeds its ceiling.

All four current-source tests passed on Google Cloud in
591.43 seconds and matched the local widths and executed
means at both seeds. These were targeted development tests.
The downloaded archive matched its VM checksum. Compute
Engine confirmed termination after collection.

[Current-source cloud log](evidence/d4-compact-repair-20261115/cloud-current-preflight/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-current-preflight/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-current-preflight/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-compact-repair-20261115/cloud-current-preflight/vm-stop.json)

## OpenSpec disposition

The reproduced controls and compact stage screens support the
no-go decision for the tested variants. The mixed full-weight tail
and resource qualification remain open. Candidate freeze, complete
new matched-batch verification and official pooled pricing require a
qualifying successor. The original banked component remains selected.
