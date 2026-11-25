# Scope of the sigma12 identity

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0. Credits: Opus and Astra.

This note supplements, rather than replaces, the queued exhaustive source and phase proof.

Write B=P12+P13−2P14, so −2≤B≤2. The unwrapped initializer is R=4094−3v+B. Except at v4095,B=−2 it lies in the signed14-bit range. The next exact signed feed is

`Rnext = 2R + (2*sigma12−1)*(4096+v) + sigma12 + P11−P12`.

The identity is sigma12=v11 XOR(v10 AND NOT sigma13). Its four root quadrants explain why only a narrow final-root exception needs checking:

| Root v | Required relation | Reason |
|---|---|---|
|0..1023|sigma12=0|R≥1023|
|1024..2047|sigma12=NOT sigma13|For sigma12=0 the next remainder is negative and does not wrap; for sigma12=1 it is positive and does not wrap|
|2048..3071|sigma12=1|R≤−2048|
|3072..4094|sigma12=sigma13=1|Both remainders are negative and inside their signed range|
|4095|sigma12=sigma13=1 when U≥−8192|Negative U in this range has P13=1, excluding both dangerous initializer/first-feed wrap patterns|

At the pinned model's final root, C=4096 and U0=−8. Every rounded signed-digit term is the exact corresponding power of two, except the top term8193. With q=h+512 this gives

`U = −16h−15−q9`.

The final root bin has n≤4194303, hence h≤510. Therefore U≥−8176 across that whole normalized root bin, stronger than the sufficient −8192 bound. This argument must remain pinned to this coefficient and seed; it is not a claim for an arbitrary future model.

Actual original inputs at that root can have positive h and negative U. For example x1048575 gives k1, n4194300, h507 and U−8128. Consequently neither h<0 nor U≥0 is a valid premise. The exhaustive receipt must retain the unrestricted abstract counterexamples separately and report the actual root4095 minimum.

The HMR repayment itself is exactly Clifford: its Boolean exponent is the measured outcome times `[sigma12 XOR v11 XOR v10 XOR(v10*sigma13)]`, which vanishes when the identity holds. Reconstruction uses the identical Boolean polynomial in a fresh zero owner and costs one CCX. Thus every possible retirement measurement outcome is covered by the same identity; no probability or average-error assumption is involved.
