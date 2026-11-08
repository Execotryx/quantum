# Inverse-square-root model-only screens

The screens compare against the 155-qubit, 28/20/14 lattice control, KMB
SHA-256 `c487332fe965389191c8e6d34848d61c82748e5802c6e616eb0363869f92c4c9`,
complete cost 509,471.48. Existing control and confirmation receipts remain pinned.

- Load-as-you-go c2: native row slices give 146 qubits for the inner stage,
  155 for the outer stage and 141 for the outer stage without c2. Re-erasure
  and reload add 56 and 766 Toffoli-like gates. Even the optimistic assumption
  that no other stage exceeds 146 qubits gives cost 599,901.27, so close this
  screen as a no-go. This is not a complete emitted circuit.
- Two-octave geometry: an ideal 256-row tree saves 275 lookup and repair
  Toffolis relative to the native-calibrated 384-row tree, while four added
  controlled rows cost 162. With unchanged 155-qubit width, unchanged margin,
  and free address selection, estimated cost is 491,956.48, 3.44% lower. The
  optimistic screen exceeds its 3% threshold, so leave it open: realistic
  address mapping, exact table geometry, fitting, and full-domain accuracy have
  not been priced or checked. No circuit was emitted or promoted.
- Registered the separate 40-hour compact-architecture research tranche. The
  bookkeeping estimate removes a 39-qubit output and adds a hypothetical 30–36
  qubit gradient, leaving 146–152 qubits if nothing else changes. It is not a
  lower bound. Direct rotation removal alone leaves 3,046 Toffolis; gradient
  preparation and cleanup remain unpriced. No 20% complete-cost prediction or
  prototype exists.

Native primitive counting, a byte-for-byte reproduced model receipt, Ruff,
Pyright with the frozen Ubuntu interpreter, and strict OpenSpec validation
passed. Detailed assumptions and numbers are retained in
`docs/evidence/invsqrt-lattice-20261108/model-only-screens.json` and
`docs/evidence/invsqrt-lattice-20261108/compact-bookkeeping.json`.