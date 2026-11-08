## 1. Backend behavior

- [ ] 1.1 Run the freed-nonzero fixture through the pinned DQI verification path. Record whether it yields per-shot value errors or aborts.
- [ ] 1.2 If it aborts, record the result and stop this change.

## 2. Depth selection

- [ ] 2.1 Register `s₀`, the chunk layout and the stop conditions in `tools/dqi_history_depth.py`.
- [ ] 2.2 Run 100 chunks of 100,000 samples on 16 workers. Record per-chunk hashes, the `n_ret` histogram, degree checks and wall time.
- [ ] 2.3 Apply the stop conditions, then select `h` by the rule. Record the decision.

## 3. Stack

- [ ] 3.1 Implement push F1–F8 and pop R1–R3 in `src/qcompile/dqi/history_stack.py`, with `W` and `K` persistent.
- [ ] 3.2 Native no-overflow fixtures at `h = 1, 2, 3`.
- [ ] 3.3 Native single- and repeated-overflow fixtures: flags zero, `K` as specified, value error reported.
- [ ] 3.4 Mutation fixtures for F5, the tag constants and R3.

## 4. Supersede

- [ ] 4.1 Replace the history bullets, overflow task and overflow scenario in `assemble-routed-bm-direct-forney-decoder` with references to this change. Update its register layout to `20h + 21`.
- [ ] 4.2 WSL tests, Ruff, Pyright, strict OpenSpec validation and a dated change log.
