# Joint cost screen for score 35

Version 221 of manwithacat's catalog adds no circuits. Its updated chemistry assembly combines 14 loaders from goodpjw2008 and one from maoxin123 with goodpjw2008's v26 factorization. The catalog reports a verified cost of **249,131,639.60**, tied with its best intact public family. Substituting that cost into the existing cloud comparison projects **33.20654**. Using the reproduced DQI and source-built inverse-square-root costs projects **33.11831**. Both are component-cost projections. [Catalog v221](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits/versions/221) · [Source and projection receipt](evidence/aggregate36-20261126/joint-score35-v221.json)

## Paired component targets

The inclusive score-35 cost-product ceiling is approximately `3.9723446102471964e24`. The remaining DQI allowance is that ceiling divided by the two companion costs. At fixed DQI width, the verifier charges mean Toffoli-like gates times width squared times the repetition factor. The following ceilings use the pinned 102,400-shot failure factors. [Portfolio audit](../tools/dqi_aggregate_audit.py) · [Failure factors](evidence/aggregate36-20261126/degree35-above35-controls.json)

| Inverse-square-root cost | Chemistry cost | DQI cost ceiling | DQI gate ceiling, 900 qubits and 0 failures | DQI gate ceiling, 888 qubits and 8 failures |
| ---: | ---: | ---: | ---: | ---: |
| 56,000 | 230M | 308.412B | 319,623 | 319,796 |
| 57,000 | 235M | 296.554B | 307,335 | 307,501 |
| 58,000 | 230M | 297.777B | 308,602 | 308,769 |
| 58,000 | 235M | 291.441B | 302,036 | 302,199 |

The 56,000 and 230M pair can fit the source DQI's measured **305.042B** zero-failure price. The same 900-qubit decoder is limited to **311,325** mean gates if a future draw has eight failures, below the measured roughly 316,131. The 58,000 and 230M pair gives the 888-qubit decoder about 308,769 gates at eight failures, which is about 7,362 below the published source gate count. The lower width requires an emitted decoder. Matching the old mean gate count or failure rate at a new width requires measurement. [Source component measurements](evidence/aggregate36-20261126/public-frontier-v220.json)

At the v221 chemistry effective normalization and the current 6,500 fixed gates, a cost of 230M allows **2,802** ANGLE gates per pass at 405 task qubits, versus **3,306** today. At 235M the cap is **2,934**. Keeping the loader and width fixed instead requires effective normalization at or below **43.31156** or **44.25312**, respectively. Such a chemistry component needs equivalent word transitions at lower loader cost, a valid refit with lower effective normalization, or both. The DFTHC literature co-optimizes the factorization and spectral amplification. Its estimates do not establish the decoded residual or the heuristic width of a new circuit here. [DFTHC and spectral amplification](https://arxiv.org/abs/2502.15882) · [Chemistry refit evidence](aggregate-above-36-implementation-26-11-2026-07-19-40.md)

## Source compatibility

SelectCopy and sequential packets offer reversible lookup layouts with different workspace costs. The dense encoding variant reads a table bit into phase and uses coherent Hadamard gates on the output to turn that phase into an XOR update. Kickmix supports X-basis measurement with reset. Direct use of that dense value-loader construction would require a different lowering that preserves the ANGLE values and phase on both endpoints. [SelectCopy](https://arxiv.org/abs/2605.20334) · [Dense encoding, Section II](https://arxiv.org/html/2610.02321) · [Kickmix gate set](https://arxiv.org/html/2610.23832v2#S2.SS1)

Published DQI field multiplication improvements must be compared with the particular decoder's recovered arithmetic. The local rank-42 transplant audit found no saving at the already rank-42 D4 sites. The source-built Tony Li decoder's generated D16 substitutions account for only 616 static Toffolis, so replacing those substitutions alone would leave the 7,362-mean-gate gap in the 58,000 and 230M scenario. The large decoder stages need a separately mapped improvement. [Field multiplier audit](dqi-multiplier-audit-15-11-2026-15-21-00.md) · [Source stage measurements](aggregate-above-36-implementation-26-11-2026-07-19-40.md)
