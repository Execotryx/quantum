# Project instructions

- Official verifier sources are authoritative; record file hashes and defining
  symbols in `contracts/contract.json`, including supplementary sources for
  imported constants or cross-file conventions.
- Resolved critical discrepancies require unchanged pinned evidence and an
  explicit resolution. Preserve per-benchmark receipts separately from the final
  metric completion report; a component receipt does not prove overall acceptance.
- A source-reconciled specification is not evidence of full baseline acceptance.
  Preserve unresolved measured gates until complete actual verifier results exist.
- DQI failure counts are the sum of disjoint `value_errors` and `phase_errors`.
  Backend confirmation mappings may use a list of distinct source counter paths.
- Run Pyright on changed Python files and run relevant tests in Ubuntu WSL with
  Python 3.13 for the supplied Linux kickmix binary. Use the frozen dependency lock.
  For the isolated environment, pass `--pythonpath vendor/linux-env/bin/python`
  to Pyright instead of relying on automatic environment discovery.
- Preserve dated Markdown change logs under `docs/`; use OpenSpec for plans.
