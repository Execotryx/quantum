## 1. History depth

- [ ] 1.1 Register seeds and run the classical routed recurrence on 10,000,000 sampled inputs. Record the retained-discrepancy distribution and per-round maximum locator degree.
- [ ] 1.2 Fix `h` by the rule in the design. Stop the change if any sampled degree exceeds `min(r, 35)`.

## 2. Full-width round

- [ ] 2.1 Implement `bm_full_round.py`: active width `a_r`, circular template view with classical offset, and a per-round branch bit.
- [ ] 2.2 Pass the frozen round-state fixtures of `freeze-dqi-zero-discrepancy-round` with the full-width round, including `Δ = 0` with `T_0 ≠ 0` and the counter increment.
- [ ] 2.3 Implement `history_stack.py` as specified in `specify-dqi-history-overflow` (push, tag-matched pop, overflow count) with native fixtures for push, pop and overflow.
- [ ] 2.4 Native forward and reverse round fixtures at `a_r ∈ {3, 12, 36}` against the classical recurrence.

## 3. Evaluator

- [ ] 3.1 Implement `inplace_evaluator.py` exactly as in Step 3, plus its reverse.
- [ ] 3.2 Native fixtures with arbitrary nonzero `σ_0`, every reduced weight, and restoration.

## 4. Assembly

- [ ] 4.1 Implement `routed_decoder.py` and `tools/dqi_routed_decoder.py` for any `(m, n)`.
- [ ] 4.2 Verify `(63, 4)` and `(127, 12)` against the oracles with the mutation and overflow fixtures.
- [ ] 4.3 Emit `(4095, 70)`. Record width, counts, serialized size, time and memory.

## 5. Full-size measurement

- [ ] 5.1 Run the matched 2,560-shot development pair against the reference on the cloud VM.
- [ ] 5.2 Run five registered salts at 102,400 shots. Price at `k_max + 2` failures.
- [ ] 5.3 Apply the admission gate.

## 6. Promotion

- [ ] 6.1 Freeze bytes. Run the full verifier and a fresh-salt confirmation.
- [ ] 6.2 Build the paired archive and hand it to `sequence-hybrid-releases`.
- [ ] 6.3 WSL tests, Ruff, Pyright, strict OpenSpec validation and a dated change log.
