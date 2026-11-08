# DQI compressed end-state proof and two-bank oracle harness

The pinned syndrome series is `S_k = sum_j e_j X_j^(k+1)`, with `X_j = alpha^j` and locator roots `X_j^-1`. For at most `t = n/2` nonzero error positions, the first `2t` syndromes determine the error vector uniquely: the difference of two such vectors has at most `2t` distinct nonzero field points, and its first `2t` power sums form a nonsingular Vandermonde system. Thus its normalized locator `sigma` is determined. Its distinct roots make `sigma` square-free.

Define `omega = sigma*S mod z^w`, `Psi = (sigma')^-1 mod sigma`, and `g = omega*Psi mod sigma`. A valid locator has constant coefficient one. Given `(sigma, omega)`, division of the series by `sigma` uniquely reconstructs every one of the `n` syndrome coefficients. Conversely, the syndrome determines the normalized locator and then `omega`. Since `sigma` is square-free, `sigma'` is invertible modulo `sigma`, and the maps `omega -> g` and `g -> (g*sigma') mod sigma` are inverse on polynomials of degree less than `w`. This proves the end-state bijection on the correctable error domain; arbitrary syndrome sequences outside that domain are not asserted to be decodable.

The fixed bank stores `sigma_1..sigma_w`, followed by exactly `w` coefficients of `g`, then zero padding. A separate unsigned weight register holds `w`: it needs two bits for `n=4` and six bits for the pinned `n=70`. At weight zero `sigma=1`, the bank and weight are zero, and the recovered syndrome and applied phase are zero. At a root, `g(X_j^-1)=omega(X_j^-1)/sigma'(X_j^-1)=e_j` under the pinned Forney convention. For the trace-dual mask `mu(E)=sum_i E_i dual_i`, linearity and `Tr(dual_i*e)=e_i` imply `Tr(mu(E)*g(X_j^-1))=popcount(E & e_j) mod 2`. Existing pinned-field tests compare the identity against `recover_forney` at each weight 0–35.

The two-bank W3 oracle harness uses XOR computation and its inverse on the valid, clean-target subspace. Its stages are:

| Stage | Live information | Bank state |
| --- | --- | --- |
| Input | Original syndrome S | Source S; destination and weight zero |
| Forward oracle | S and its exact `(w, sigma, g)` | Source S; destination bank and weight hold the end state |
| Inverse oracle | End state determines S | Source XOR reconstructed S is zero; destination and weight remain live |
| Reverse transfer | End state reconstructs S and S recomputes the end state | Source S; destination and weight are cleared |

The current harness invokes classical polynomial oracles; it is not a reversible gate implementation, does not establish their scratch cleanup, and is not a single-bank transform. At full size, these two simultaneous 70-word banks plus six weight bits require at least `2*70*12+6 = 1,686` qubits before oracle scratch, exceeding the 900–1,000 target. Reject this two-bank layout for that target; this is not a rejection of every possible W3 layout.

The finite-domain test exhausts every correctable GF(16) error pattern with `n=4`, `t=2`, field polynomial `0x13` and all 15 nonzero locations and magnitudes: `1 + 225 + 23,625 = 23,851` patterns. It observes exactly 23,851 distinct syndromes and encoded states, checks restoration and zero padding, and evaluates `g` at every occupied root. It does not exhaust the other 41,685 four-word syndrome sequences. Separately, one deterministic pinned GF(4096) case at each weight 0–35 round-trips and checks all occupied roots. The receipt and source/test hashes are in `docs/evidence/dqi-inplace-20261108/summary.json`. All 38 focused WSL tests, Ruff and Pyright passed. W1/W2 programs, reversible oracle circuits, compressed-width projection, routed-decoder admission and promotion remain open.
