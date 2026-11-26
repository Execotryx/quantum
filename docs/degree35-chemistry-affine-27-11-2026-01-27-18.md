# Chemistry affine endpoint screen and score-35 resource limits

The ANGLE endpoint checker now searches the full binary affine span
of live wires for a product control. Value updates use every legal
forward and reverse input and exclude their target wire. For a phase
gate, equality is required on the rows where its target is one.
The rewrite carries the original classical guard onto every
replacement gate. A native fixture replay confirmed fewer charged
gates and equal phase and scratch across matched measurement outcomes.

The pinned goodpjw2008 public comparison has 1,219 legal addresses
and 15 loaders. The screen examined **3,307** charged products on
both endpoint families and found **zero** replacements. Reassembly
reproduced all 15 original KMB hashes. The pinned chemistry verifier
passed **78,016** trajectories at **249,169,842.41339546** cost, with
**405 task qubits** and **3,307 ANGLE Toffolis per pass**. This
reproduces the previous cloud component price.
[Public source and original hashes](evidence/aggregate34-20261126/public-cloud-registration.json)
· [Registration](evidence/aggregate36-20261126/chem-affine-endpoints-registration.json)
· [Per-loader screen](evidence/aggregate36-20261126/chem-affine-endpoints-screen.json)
· [Full chemistry verifier receipt](evidence/aggregate36-20261126/chem-affine-endpoints-native.json)

At the other two measured public costs, reaching 35 needs chemistry
at or below **212.763M**, a **14.61%** reduction. With the measured
normalization and 6,500 fixed heuristic gates, 405 task qubits allow
at most **2,348 integer ANGLE gates per pass**. Even a hypothetical
one-word batch at 377 task qubits allows only **2,764** per pass.
The current heuristic temporary allocation is 287 qubits, compared
with 82 in the ANGLE loaders. Shrinking the ANGLE scratch alone
therefore leaves chemistry's charged width unchanged.

If DQI alone supplies the gain at the same executed gate count and
failure penalty, the 900-qubit public decoder would need at most
**831 declared qubits**. The 70 syndrome words already occupy 840.
The equivalent bound for the source-built components is 827 qubits.
Both bounds are conditional on holding the other component costs
fixed. The highest full cloud comparison remains **33.20483975**.
[Cloud comparison costs](evidence/aggregate34-20261126/public-cloud-audit.json)
· [Source-built component costs](evidence/aggregate36-20261126/public-frontier-v220.json)
