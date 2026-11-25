# Public inverse-square-root admission

Reviewed on 2026-11-15. All three published output hashes match the
registered hints. The fixed source search found no complete generating
source for those bytes. Each candidate is classified `binary_only`; the
decision is `no_go`. The confirmed v6 member `254279d6…` stays eligible.

## I1

- Published SHA-256 `bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47`.
  The downloaded file and the pin from [Özer's v18 portfolio](https://www.kaggle.com/datasets/ahmedberatozer/vqcc-v18-portfolio)
  both match. The portfolio is marked Other; its credits license Özer's
  changes under Apache-2.0 and preserve upstream terms.
- [Ehan Mallick's notebook, v2](https://www.kaggle.com/code/ehanmallick/invsqrt-20-65-two-3-to-2-and-merges-on-y6225)
  supplies two Apache-2.0 patches starting from the compiled yoyobar
  circuit `67482db6…`. Downloaded notebook SHA-256
  `c45fe46650cfb59db0901243d23d50cf95e7300fa5a1a98208f7e9585cac09ad`.
- [Yoyobar's notebook, v8](https://www.kaggle.com/code/yoyobar/lb-22-99-invsqrt-101-62-qubits)
  packages the exact `67482db6…` circuit from its attached release.
  Downloaded notebook SHA-256
  `cd0503d0e162e52033d97447e237c5cd32d564ec1fb637d956ef910e74e6daaa`.
  The exact 62-qubit parent generator was unavailable in this lineage.

## I2

- Published SHA-256 `af4698478fbad775a5a271690cf4c2d8783caf0b8d12048106d1973c4ac6862e`.
  The downloaded file from [Banerjee's ladder-parts dataset, v8](https://www.kaggle.com/datasets/somejoint/qcc-ladder-parts/versions/8)
  matches the [EigenOS v7 ledger](https://github.com/EigenOS-Quantum/eigenos-vqcc/blob/f4dd22d26a31b23a24db25ef461ddff4efcc3f85/NOTICE-v7.md).
  Kaggle identifies the dataset as Apache-2.0.
- [Banerjee's public assembly notebook](https://www.kaggle.com/code/somejoint/quantum-circuits-24-65-local-gm-chem-refit),
  SHA-256 `2936297281f9cee447e8c1820e0948e514c6ce1d41d3275dac506f01a6ecbce9`,
  documents two forced phase bits on the author's v33 circuit
  `80ac3d48…`. The program packages pinned members. The exact v33
  generator and its required source chain were unavailable.

## I3

- Published SHA-256 `9a8627c812833a6feca6eb82239f38d1a9a5e1eee299a9a7af9abd85e36339be`.
  The downloaded file from [Busyaprime's member dataset, v5](https://www.kaggle.com/datasets/busyaprime/33-qcc-v8-members/versions/5)
  matches. Kaggle identifies the dataset as Apache-2.0.
- [Busyaprime's renamed notebook, v10](https://www.kaggle.com/code/busyaprime/lb-25-33133-grimoire-33-every-gate-a-pixel/versions/10),
  SHA-256 `5a16e646ac6d58a022c067467404aa4d2e37cb7f99666fb49dc7231745919090`,
  locates and copies the exact precompiled file from dataset v5. It
  describes both Boolean resynthesis passes, including the 25-AND S1
  window. The released source for those exact rewrites was unavailable.
- [MrMeows's open-circuits dataset](https://www.kaggle.com/datasets/mrmeows/qcc-1375-open-circuits)
  includes generator sources for upstream designs, including a documented
  63-qubit source with measured cost 103,672.22. Busyaprime's pinned
  member is a separate output with cost near 102,349.22.
