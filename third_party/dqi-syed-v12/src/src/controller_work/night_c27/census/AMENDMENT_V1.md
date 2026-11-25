# C2.7 quadratic-node census amendment, version 1

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
Credits: Opus and Astra.

This amendment is written before any new-law sampler draw in this restored
execution session. It preserves the original fixed sample size **500,000,000**,
seed **202611112245**, and total confidence error **2^-128**. It does not erase,
rename, or reuse results from the earlier reduced-locator census. The preserved
plan is identified in `C27_paper_recovery/RESUME.md`; the old implementation and
small infrastructure results remain under `controller_work/night_root/`.

## Fixed candidate and predicates

The primary candidate accepts physical error weights j >= 15. Cutoffs 16 and 17
are precommitted secondary reports on exactly the same draws. All three reports
will use delta = 2^-128 / 3, so their simultaneous confidence error is at most
the preserved 2^-128. There is no early PASS, seed selection, node selection,
or cutoff selection during this run. A stopped prefix is incomplete even if its
temporary confidence bound is small. If the algorithm, nodes, input law, or
acceptance predicate changes, a new amendment and distinct state are required.

The field is the supplied GF(4096) polynomial basis, modulus 0x1053. The common
quadratic extension has theta^2 + theta + 2048 = 0. For i = 0..34, set

    t_i = 2*i
    kappa_i = 2048 + t_i^2 + t_i
    q_i(x) = x^2 + x + kappa_i.

Here additions are XOR and multiplication is in the supplied field. These 35
irreducible quadratics are fixed before sampling. Set U = product(q_i).
For support roots a and nonzero magnitudes e, form

    Lambda(x) = product_a (x+a)
    Omega(x) = sum_a e*a*U(a)*Lambda(x)/(x+a).

Classify the active polynomial recurrence, starting (N,D)=(Omega,Lambda), at
i=0..j-1. A zero N mod q_i or D mod q_i is a finite failure. At the first such
failure, record the index and kind and stop this active recurrence; there is no
unjustified continuation through a pole. Otherwise set P=(D/N) mod q_i and
(N,D)=((D+P*N)/q_i,N). Exact divisibility and terminal (N=0,D nonzero constant)
are checked in the reference and validation builds.

Independently construct the full denominator

    G = Lambda * x^[j even] * product(q_i : i=j,j+2,...,33-[j even]).

It has degree 35 and is squarefree. Its monic representative suffices because
nonzero scalar gauge does not change half-Euclidean degree profiles. Let
A=sqrt(G_odd), B=sqrt(G_even) with the top even coefficient eliminated by A,
exactly as in the degree-35 branch of `night_converter/night_outer.py`. Save the
entire descending Euclidean degree mask. The native full-35 core rejects a
nonconstant gcd, a degree drop > 2, simultaneous drop-2 starts {17,15}, or
simultaneous drop-2 starts {14,12}. Both window exclusions are retained: this
candidate invokes Core.frame(17), not the earlier optional reduced-degree outer.

For cutoff c in {15,16,17}, the counted union is

    j < c OR active finite failure OR full-half-core rejection.

No uniformity assumption about any intermediate field value is used.

## Exact input law and numerical control

The official verifier specifies m=4095, n=70, q=4096, r=2016. Error weight j has
probability w_j^2, where w is the normalized principal eigenvector of its
36-by-36 tridiagonal DQI matrix. Conditional on j, support is uniform without
replacement among all 4095 nonzero field elements, and magnitudes are independent
uniform elements of {1,...,4095}. Classical MBUC weights do not enter these
failure predicates and are not sampled. This does not reproduce the official
NumPy random bitstream or constitute an official verifier run.

The executable configuration will use the preserved exact rational spectral
vector in `milestone132/logs/cutoff-budget.json`, normalized by its exact squared
norm, together with that certificate's explicit total-variation bound. Its
36 weight masses will be quantized by cumulative floor to 64-bit bins; the
exact total-variation error of that operation will be recorded and added to
every final probability upper bound. This is an explicitly bounded numerical
approximation to the official law, not a claim of exact irrational sampling.
Support and nonzero magnitudes use rejection-based unbiased bounded integers.

The PRNG is std::mt19937_64 with the preserved seed. As in the inherited census,
binomial confidence statements use the ideal independent-draw interpretation
of the deterministic PRNG. This assumption is explicit. It is distinct from
assuming that the intermediate arithmetic values are uniformly distributed.

## State, diagnostics, and validation separation

The sampler is streaming. It saves the exact PRNG state, completed draw count,
weight histogram, joint reason histogram, finite-failure index diagnostics,
and full half-degree-profile histogram. State writes are atomic and bind the
configuration/source hashes. SIGTERM or SIGINT stops after a completed draw,
saves state, and exits with an incomplete status. One root-owned memory guard
starts every heavy run; this agent will not start a large census.

Small reference/replay/resume tests use a separate validation seed and separate
files. They never count toward the fixed 500-million production draw and do
not provide a useful rare-event certificate. The production state must remain
absent until the root launches the guarded run. The final report must include
actual N, actual union counts, CP upper bounds at delta/3, spectral and binning
variation, source/configuration hashes, and whether the fixed N was completed.

This amendment is a sampling plan only. It does not certify failure probability,
T count, Q, phase correctness, or any completed checkpoint.
