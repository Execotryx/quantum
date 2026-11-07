# Next hybrid optimization plan

This planning change reconciles the attached 7 November investigation
with the certified hybrid and pinned verifier. Three Astra investigations
ran in parallel and covered DQI, chemistry and inverse square root. The
certified archive and previous campaign records remain the controls.

| Order | OpenSpec | First implementation decision |
| --- | --- | --- |
| 1 | [Shared verification](../openspec/changes/prepare-next-hybrid-verification/proposal.md) | Preserve historical records while binding full coverage, package checks and confirmation to the actual candidate. |
| 2 | [Qubit-first DQI](../openspec/changes/prototype-qubit-first-dqi/proposal.md) | Prove the runtime-mask phase path and compare exact reversible EEA and BM slices before choosing a full decoder. |
| Parallel | [Chemistry refactorization](../openspec/changes/screen-dfthc-refactorization/proposal.md) | Reproduce J8 and J9, then use a bounded weight-only pilot and screen decoded factors before generating loaders. |
| Parallel | [Compact inverse square root](../openspec/changes/screen-compact-invsqrt/proposal.md) | Test a minimax quadratic against the certified direct circuit with exact row-level arithmetic and exhaustive coverage. |

Each change contains a technical design, a sequenced implementation
checklist and testable requirements. Their promotion gates use measured
costs and fresh confirmation. The report's frontier figures inform
research targets. They are recorded separately from local results.

The plans correct four implementation assumptions. The DQI verifier
needs a fresh classical mask on each shot. Chemistry fixes its
preparation precision and derives coverage from the candidate factor
shape. The inverse-square-root arithmetic cannot overwrite a lossy
Horner accumulator without retaining or reconstructing information.
The pinned metric already defines the relevant package limits and its
actual array dtypes.

The shared plan owns integration. Design and numerical investigation
can start independently. Native full runs start serially and use
measured memory headroom. External submission and cloud execution are
outside this planning change.
