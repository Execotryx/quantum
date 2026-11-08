## Why

The v3 inverse-square-root circuit declares **159** qubits. Its liveness
profile reports at most **131** allocated qubits. Cost is
`declared qubits × (Toffoli + T/4 + rotation charge)`, so the 28-qubit
gap is worth up to **17.6%** of the component cost, or ×1.067 on the
aggregate.

The roadmap recommended an id-remap pass. The code shows two possible
causes, and only one of them is fixed by a remap.

- **H1, ids not reused.** Freed ids are not handed back, or the count
  is a high-water mark of ids touched. A semantics-preserving remap
  closes the gap.
- **H2, transient workspace inside primitives.** `build_circuit` samples
  `num_allocated_qubits` only at four stage boundaries (`lookup`,
  `arithmetic`, `phase`, `after_unlookup`). Carry ancillas and other
  temporaries allocated inside `_add_row`, `iadd` and `isub` are live
  between those samples. A remap cannot remove live qubits.

The sponsor paper states that the kickmix builder hands freed qubits back
to later allocations, so H2 is the more likely cause. This change measures
the cause before building either fix.

## What Changes

- Add a shared liveness tracer: a builder proxy that samples allocation
  after every call, plus an op-stream interval analysis of the serialized
  circuit.
- Establish how the verifier counts qubits with dense and sparse id fixtures.
- Branch on the measured cause: an interval-colouring remap for H1, or
  width-aware arithmetic candidates for H2, each priced by the measured
  qubit-to-Toffoli exchange rate.
- Apply the tracer to the reference DQI circuit and the chemistry ANGLE
  circuits. DQI cost scales with the square of its width.
- Verify, confirm and archive any qualifying circuit.

## Impact

- Code: new `src/qcompile/liveness.py`; `src/qcompile/invsqrt/direct.py`;
  `tools/invsqrt_direct.py` protocol 4; `configs/invsqrt-direct-v4.json`.
- Control: v3 KMB `ce8a58b6…f5b4`, cost 548,860.92.
- Risk is low for a remap (byte-level id rewrite, exhaustive verification)
  and moderate for adder changes (new arithmetic, new model recurrence).
