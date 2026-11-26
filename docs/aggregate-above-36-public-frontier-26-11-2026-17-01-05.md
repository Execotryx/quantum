# Public component costs and the remaining DQI budget

The pinned version-218 catalog lists 135 inverse-square-root circuits,
161 DQI circuits, and 472 chemistry families. I filtered each component
to finite positive costs. Inverse square root and chemistry use the
catalog's single-task verifier cost. DQI uses the smallest recorded
zero-failure cost for the optimistic case and the smallest published
multi-draw expected cost for a separate comparison.
[Catalog version 218](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits/versions/218)
· [Pinned rows, source hashes, and calculations](evidence/aggregate36-20261126/public-frontier-v218.json)

| Component | Selected public cost | Cost required to exceed 36 if the other two optimistic costs hold |
| --- | ---: | ---: |
| Inverse square root | 60,927.55 | Below 48,036.54 |
| DQI with zero failures | 305.030B | Below 240.492B |
| Chemistry | 249.132M | Below 196.421M |

The optimistic combination projects **33.25742**. Substituting Tony Li's
published **305.801B** expected DQI cost projects **33.22945**. Even the
optimistic product must decrease by more than **21.16%** to exceed 36.
The catalog's 08:37 UTC leaderboard snapshot reports **34.50408**.
It does not identify the leading circuit files or their component costs.
[Tony Li's published source](https://www.kaggle.com/datasets/tonylica/quantum-ai-32-85306-task-generators/versions/2)

The catalog's DQI structure card for the exact Tony Li parent has no
stage labels. The repository's independent native trace accounts for
the full circuit and remains the source of stage costs. The catalog's
cheapest inverse-square-root member is a derived circuit with no
generator reference. The inspected chemistry notebook is version 25,
one revision newer than the best indexed chemistry member. It contains
loader-building recipes and depends on two other notebook outputs.
The indexed version-24 members remain external measurements.
[Native DQI trace](evidence/aggregate36-20261126/dqi-source-stage-boundaries.json)
· [Chemistry notebook](https://www.kaggle.com/code/goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25737)

The pinned DQI verifier's repetition formula gives these strict
mean gate ceilings when the catalog's inverse-square-root and chemistry
costs are held fixed. Failure counts apply to 102,400 trials.

| Declared qubits | Zero failures | One failure | Eight failures |
| --- | ---: | ---: | ---: |
| 879 | 261,286.20 | 260,091.70 | 254,502.34 |
| 888 | 256,016.70 | 254,846.28 | 249,369.65 |
| 900 | 249,235.10 | 248,095.69 | 242,764.13 |

At 879 qubits, the measured 194,493-gate phase stage leaves **66,793.20**
gates even with zero failures. The optimized first locator reciprocal
and its inverse cost **72,708**. At the unchanged 900-qubit source width,
the measured **316,102.19**-gate decoder would need a reduction exceeding
**66,867.08** mean gates. Holding the other stages fixed would leave
about **10,079** gates for a replacement of the existing 76,946-gate
field-to-root phase stage. A replacement built from the current
45,045-gate supplied-residue scan alone already exceeds that ceiling.
The public-companion route therefore needs savings across multiple
decoder stages or a different phase algorithm. The best full cloud run
on a local archive remains **33.20483975**.
[Native middle-product results](aggregate-above-36-dqi-middle-product-26-11-2026-16-47-11.md)
· [Supplied-residue scan](aggregate-above-36-dqi-residue-scan-26-11-2026-07-46-21.md)
