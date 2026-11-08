## Why

A compressed factorization from `fit-compressed-dfthc-factors` fixes `λ_eff`,
the preparation cost and the persistent width. The ANGLE loaders then
decide most of the remaining Toffolis. With 8-bit words at `(9, 143, 40)`,
the structural model gives 6,741 preparation and rotation Toffolis. The
loaders run twice per evaluation, once forward and once in reverse.

Loader choice spans about a factor of three in chemistry cost (estimates at
`λ_eff = 48`):

| Loader | Circuits | ANGLE Toffolis per pass | Scored qubits | Chemistry ratio |
| --- | ---: | ---: | ---: | ---: |
| Unary, `J = 5` | 15 | about 21,500 | 428 | about 3.3× |
| Unary, `J = 9` | 9 | about 12,900 | 460 | about 4.7× |
| Banked unary, `J = 13` | 6 | about 8,600 | 492 | about 5.9× |
| Monomial loaders, `J = 5` | 15 | about 4,500 if the table structure allows | 428 | up to about 10× |

A unary loader costs about one Toffoli per address per circuit, whatever
the word width. Packing more words into each circuit, up to the 128-qubit
cap, therefore pays. Monomial loaders share address products across all
output bits, and their cost depends on the word table's structure.

## What Changes

- A shape-generic banked unary loader as the first candidate, with `J`
  chosen at the 128-qubit cap.
- Monomial (algebraic-normal-form) loaders that use invalid addresses as
  don't-cares, a high/low address split, measurement erasure of products,
  and a paired-product step. These are derived independently from the
  public technique description.
- A per-vector sign gauge that reshapes the word table without changing
  the Hamiltonian, to cut the monomial count.
- Full chemistry verification with the new coverage and promotion into
  the archive.

## Impact

- Code: `tools/banked_chemistry.py` generalized; new
  `src/qcompile/chemistry/loaders.py`; `tools/hybrid_preflight.py` checks
  for the new layout.
- Depends on an eligible factorization from `fit-compressed-dfthc-factors`.
- Changes the chemistry NPZ, tree and ANGLE family. The old chemistry
  confirmation does not carry over.
