# RN2-B: the same leading-one route with implicit P21

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

This is a separate, unexecuted refinement of RN2-A. The earlier source and
manifest are retained. The complete proposed delta remains -1E with unchanged
T/R/accuracy and unchanged inverse, but local forward peak stays46 rather
than rising to47; the total local HMR-symbol count stays31.

Keep only the original20 prefixes. Clear the leading-one indicators at input
positions2..21, which need only P0..P20. The top owner x21 is now zero, while
original x0,x1 remain available. Compute directly into x21:

    H = 1 xor P1 xor ... xor P20 xor (P20 * (1 xor x1)).

This costs one AND in an intended output owner, with no new helper or HMR
debt. The missing P21 is now the affine expression

    P21 = H xor1 xor P1 xor ... xor P20.

Clear original leading-one positions0 and1 by XORing P21 into x0 and
P20 xor P21 into x1. All those operations are Clifford. Route the10-position
odd lane and11-position even lane, then restore the normalized leading bit
by x20 ^= 1 xor H. H remains in x21. The original20 prefix measurement
corrections apply unchanged because their final normalized H is unchanged.

Ledger:18 prefixAND +1 outputH AND +32 swaps +1 thresholdhelper =52 forward;
old44.5 inverse;96.5 complete, modeledpeak46/global48. The two lowest input
bits are not silently assumed zero or classical: their original values
control H before either is changed. All original-domain Boolean/HMR checks
and the paper allocator run again for this exact emitter under the new guard.

No native construction or current-qualified-result change is authorized by
this plan alone. Await complete exact certificate and parent review.
