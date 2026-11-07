## 1. Reconcile and test primitives

- [ ] 1.1 Pin the reference raw receipt, source and native binary, field polynomial, bit/register mapping, legal input domain and actual runtime-mask distribution.
- [ ] 1.2 Establish reduced-field exhaustive arithmetic and decoder fixtures, full-field boundary fixtures and arbitrary runtime-mask parity cases.
- [ ] 1.3 Implement and measure reversible multiply-XOR and inversion, with arbitrary targets, zero cases, inverse composition and deliberate arithmetic/cleanup mutations.
- [ ] 1.4 Build the streamed exact runtime-mask phase tail and demonstrate syndrome and scratch restoration. Measure actual stage cost before considering a reciprocal/trace rewrite.

## 2. Choose the decoder architecture

- [ ] 2.1 Profile the pinned reference by stage and write an explicit reversible layout and inverse map for EEA and BM slices, with full physical-width accounting.
- [ ] 2.2 Build and compare the two exact locator update/undo slices, including degree transitions, ties, zero discrepancies, maximal histories and register-reuse failures.
- [ ] 2.3 Select one architecture using full projected cost and proof gates. Record why the alternative was rejected or deferred.
- [ ] 2.4 Emit the exact circuit and reconcile every stage and reverse path with the classical oracles, serialized circuit and actual native counts.

## 3. Screen and hand off

- [ ] 3.1 Preregister the bounded candidate grid, matched development cases, sample and salt roles, resource budget, cost thresholds and tie-breaks.
- [ ] 3.2 Screen the exact circuit against the reference; consider a separate approximate lane only after exact correctness and cleanup have been established.
- [ ] 3.3 Freeze the selected KMB and perform full verification and one-use confirmation with disjoint value and phase counters and exact coverage.
- [ ] 3.4 Provide the deterministic recipe, manifest, resource profile and receipts to shared release integration. Retain the incumbent on a no-go.
- [ ] 3.5 Complete WSL/Pyright, required review cycles, source reconciliation, dated evidence and strict OpenSpec validation.
