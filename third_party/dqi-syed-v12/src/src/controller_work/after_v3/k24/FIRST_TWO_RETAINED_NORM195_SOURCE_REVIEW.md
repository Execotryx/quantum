# Independent source review: production first-two retained norm stack

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
Credits: Opus and Astra.

## Conclusion and scope

No source, operand-alias, measurement-phase, or stated helper-count blocker was
found in the four files pinned below. This is a read-only source review and
Python AST check. No native arithmetic, circuit construction, simulation,
statistical draw, or official verification was performed for this review.
The proposed saving is not banked by this document.

The new closed inverse requires a caller-owned, disjoint, initially zero
24-bit storage bank. Its production adapter obtains that bank only at the
actual first-two return seam: the generic reverse loop has returned the public
carry to one, the tail controller is closed, and a public X on carry bit zero
turns all 24 bits into zero. The three remaining inverse charts do not read
that carry. Each call resets every storage bit, and the final X restores one
before the original parent resets and frees the carry. The old arbitrary
initial-carry component API is not granted this promise.

## Exact value and phase ownership

Write the original GF4096 norm in its quadratic GF64 basis as N=(x,y), with
h=Norm(N), gamma=inv0(h). The reconstructed inverse is
Ninv=(X,Y)=((x+y)*gamma,y*gamma). After the two consuming field products, the
old-half HMR masks are repaid from each scaled half multiplied by the still
retained original polynomial N. These are bilinear phases with classical
masks, so they add no T gates.

The old-N mask is taken in the GF64 tower basis. The implementation restores
its exact witness using

    (x,y)=((X+Y)*h,Y*h).

It conjugates X by Y only during the first repayment and undoes that CNOT.
The child h is then measured in its quadratic GF8 tower basis. The existing
scalar inverse-phase helper expects precisely that tower-mask basis, and its
source is the retained polynomial-coordinate gamma=inv0(h). The four-T phase
therefore repays the actual h mask. Finally gamma is erased as Norm(Ninv),
Ninv is returned to polynomial coordinates, the source receives its final
quadratic conjugation, and Ninv is erased against Norm(source_inverse).
All witnesses remain live until their own debts have been paid. The zero
source maps to zero throughout, so no nonzero-half or new unit promise is
introduced.

## Resource accounting

The static count is

    42 + 15 + 20 + 30 + 84 + 4 = 195 T.

The original norm12, child norm6 and child reciprocal6 use only the supplied
24-bit bank. The cubic inverse uses ten fresh scaffold bits; reciprocal
reassembly uses twelve fresh bits; consuming halves uses the live reciprocal12
plus temporary12; the child phase uses reciprocal12 plus six phase bits.
Thus the fresh-helper peak is 24. The local production seam has 864 retained
bits, and the generic component checker deliberately retains865; both are
consistent with the global Q889 ceiling.

Only the fresh six-bit child HMR mask controls the four-T cleanup. The exact
execution count is195 minus4 when that mask is zero, giving195-4/64 under
fresh uniform HMR masks. Against the selected v4 closed inverse276-84/2^24,
three eligible production calls save243 static T and

    243 + 12/64 - 252/2^24

expected T. No extra event is added for the same scalar cleanup: the existing
scalar inverse-phase event hook already counts it.

## Checker coverage reviewed

The independent component oracle implements the original field polynomial
and K24 quadratic inverse directly. It covers all4096 points of three
structured axes, arbitrary K24 values and explicit zero sources. Closed
prefix, closed pair and old-deferred/new-closed panels check value,
nonlinear phase, storage reset, dirty bystanders and fresh scratch. The
checker copies only the actual six-bit child mask to a classical observation
register; it does not force an HMR outcome. The observed mask gives an exact
per-shot T-count oracle. Both serialized builds and all three seeds are
required, and malformed lengths, aliases, classical banks and extension
parameters are rejected before emission.

The production checker retains the original781 admitted physical inputs and
one independently prepared rare physical gauge1 input. It records the76
original key-domain exclusions explicitly. The real post-index2/tail.close
seam is saved before the bank reset, and the entire carry is tested equal to
one on all782 inputs and all three seeds. That seam and the inherited prefix
are correctly value-only because older first-two HMR debts remain open.
The complete paired key checks the unchanged independent polynomial boundary
oracle, arbitrary diagonal masks and three cubic probes, all restored input
and probe bits, and scratch. It requires216986 static key T,101058 prefix T,
Q889, three195 receipts, the exact complete HMR-event multiset, and two
identical prefix/pair/seam builds. Smoke runs retain an explicit limited-scope
label; full native and subsequent whole-candidate gates remain separate.

## Source binding

- `blocks/v5/inverse_retained_norm195.py`: `4ae6b746ff165082b8c67ae733f144c16e34ac93d03952676d404f3cfa6b9b50`
- `blocks/v5/first2_retained_norm_adapter.py`: `1abb17d7c5943d7bd6bbc389b37113f7166bdff30c29755d0e6e6633e62e80cd`
- `blocks/v5/check_inverse_retained_norm195.py`: `706f5bfc69794b542aa541f87dc0329aa7645a07f792f7c30b5ac218f79be1a7`
- `blocks/v5/check_first2_retained_norm_adapter.py`: `a3d693d4e283ace090226eb5f45f5f64ca669c9dd4efe3e0f7746630b0538ae7`
