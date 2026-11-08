# I3 chemistry continuation outcome

The registered WSL run started a fresh L-BFGS optimizer from the frozen
1,500-evaluation I3 checkpoint at shape (9,143,40). The independent
residual check reproduced 81.3991 mHa before optimization. After 5,000
additional evaluations, the continuous residual was **41.5749 mHa**,
a **48.92%** reduction from the parent. The 12-bit decoded two-body
residual was **43.9087 mHa**. The run took 2,350.90 seconds with two
BLAS threads and stopped at the registered evaluation cap.

The result is budget-limited. The continuous residual remained above the
19.0 mHa S1 gate, so it is a candidate for another separately registered
continuation. The decoded metrics are diagnostics before S2 and S3.
All checkpoint arrays remain in the ignored run directory. Their SHA-256
digests are in the ten checkpoint records.

The running process loaded the source recorded in the registration.
A zero-vector check was added to the checked-in continuation runner
after launch. The registered source is recoverable from the checked-in
runner by replacing the four lines from the `lengths` assignment through
`unit = vectors / lengths` with the original
`unit = vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)`.
The recovered bytes match runner SHA-256
`5e82282427eb86807f0fd40bf3b9ffe32afe81470e62fa09f723e7f59362474f`.
The parent checkpoint uses nonzero vectors.

[Registration](evidence/chem-s1-resume-5000-20261108/registration.json) ·
[Terminal result](evidence/chem-s1-resume-5000-20261108/decision.json) ·
[Final checkpoint](evidence/chem-s1-resume-5000-20261108/checkpoint-05000.json)
