# Open circuit shortlist for an aggregate above 36

Version 220 of **manwithacat**'s Apache-2.0 public catalog contains 774
distinct families or circuits. It adds one inverse-square-root circuit and
five chemistry families relative to version 218, with no new DQI circuit.
The best measured-cost mix projects **33.22945**. Using the cheapest DQI
zero-failure price gives **33.25742**. The former uses a 48-draw DQI estimate.
Both are projections from component evidence. Our complete cloud comparison
remains **33.20484**. The direct leaderboard request returned an
authentication error. Acceleratorer's dated report records **34.50408** as
the leading public score, with no component identities for that entry.
[Version 220 catalog](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits/versions/220) ·
[Acceleratorer leaderboard observation](https://github.com/Acceleratorer/quantum-circuit-compilation-clean#current-status-2026-11-26) ·
[Hashes and score calculations](evidence/aggregate36-20261126/public-frontier-v220.json)

| Task | Selected control | Cost and provenance |
| --- | --- | --- |
| DQI | **Tony Li / Entangled Team**, `4b5721411adc` | **305.801B** estimated from 48 draws. Two local source builds match these exact bytes. The source credits Areeb Ali and team ThemBones. [Published source](https://www.kaggle.com/datasets/tonylica/quantum-ai-32-85306-task-generators/versions/2) · [Builds](evidence/aggregate34-20261126/tonylica-builds.json) |
| Inverse square root | **prvsiyan**, `6b5921453010`, as performance control | **60,927.55**, 37 qubits. The exact bytes passed the full cloud comparison. A complete emitting source chain for this hash remains open. Use Tony Li's exact 39-qubit source build `68eb8c13ebc7` at **61,696.23** for independent source work. [prvsiyan's circuit](https://www.kaggle.com/code/prvsiyan/verifier-guided-quantum-circuit-optimization) · [Tony Li source](https://www.kaggle.com/datasets/tonylica/quantum-ai-32-85306-task-generators/versions/2) |
| Chemistry | **goodpjw2008** v26 `f2ebad6b82f6` and **Ertuğrul Özer** v67 `3e35ab135c4e` as tied performance controls | **249.132M** each, at `(R,B,C)=(9,127,46)`. Their family hashes and factorization hashes differ. The reported gain over goodpjw2008 v24 is about 1.30 cost units. For source experiments use **Acceleratorer / Accelra exp-074**, which built the goodpjw2008 v20 chemistry from source using maoxin123's parameter table. Its 15 loaders and factorization scored **249.854M** on two reported salt settings. Verify upstream licensing for any source copied from that recipe. [goodpjw2008](https://www.kaggle.com/code/goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25737) · [Ertuğrul Özer](https://www.kaggle.com/code/ozertuu/google-quantum-ai-vqcc-33-2101-sota-apex) · [Exp-074 receipt](https://github.com/Acceleratorer/quantum-circuit-compilation-clean/blob/main/evals/2026-11-26-exp074-source-built-v20-chemistry.json) |

**Matt Liston's 889-qubit DQI** `3c03fa53dd86` is the alternate
source-backed decoder. Its 48-draw estimate is **314.037B**, 2.69% higher
than Tony Li's. Its generator derives from Syed Asad Ali's work. Liston's
source package also credits team ThemBones for the chemistry and inverse-
square-root generators, and Almond Labs for the inverse-square-root recipe.
The catalog marks the DQI and inverse-square-root rebuilds byte-exact.
The chemistry rebuild is a publisher claim with a hash-check command.
[Liston's Apache-2.0 generator package](https://www.kaggle.com/datasets/mliston/vqcc-milestone-generators-32-30740/versions/3)

**Atakan Aldemir's 900-qubit DQI** `dbb2ada3a4da` supplies the optimistic
price of **305.030B**. It incorporates goodpjw2008's zero-test cuts on
the Entangled Team decoder. The catalog supplies no multi-salt estimate
for this hash. Keep it as a sensitivity check. Özer's 890-qubit DQI
`47480efbb7b9` is a secondary comparison at **309.665B** over 48 draws.
Acceleratorer exp-074 uses the same Tony Li DQI bytes and reports
**305.042B** for a 102,400-shot zero-error draw, so it does not supply a
different decoder. [Atakan Aldemir](https://www.kaggle.com/code/atakanaldemir/qcc-shared-products-and-controlled-refits) ·
[Özer's DQI](https://www.kaggle.com/code/ozertuu/vqcc-milestone-public-score-31-69497) ·
[Exp-074 receipt](https://github.com/Acceleratorer/quantum-circuit-compilation-clean/blob/main/evals/2026-11-26-exp074-source-built-v20-chemistry.json)

The best existing mix needs a **21.36%** reduction in the cost product.
Holding the other two components fixed requires inverse square root below
**47,915.46**, DQI below **240.492B**, or chemistry below **195.925M**.
At 900 qubits, the DQI target permits about **249,235 mean gates** even
with zero failures. The source control used about **316,131** in the
reported zero-error draw. The measured degree-35 suffix handoff also
exceeds the available budget when combined with the current phase route.
Use the source-backed controls to measure a lower-cost decoder or a joint
improvement across benchmarks. A submission still requires two independent
builds and full cloud metric and fresh confirmation above 36.
[Measured degree-35 handoff](aggregate-above-36-dqi-raw-suffix-prefold-26-11-2026-22-24-45.md) ·
[Certification protocol](../openspec/changes/raise-hybrid-aggregate-above-36/design.md)
