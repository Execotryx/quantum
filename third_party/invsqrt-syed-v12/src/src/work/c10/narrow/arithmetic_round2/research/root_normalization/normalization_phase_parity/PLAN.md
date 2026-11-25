# RN2-D: one shared cubic correction for forward prefix measurements

Copyright2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

This is an isolated paper-only change to normalization's own measurement cleanup. It does not touch the protected shared table cleanup, coefficient loaders, endpoint phase, angle table or oracle. RN2-B and RN2-C sources remain immutable.

At the forward normalizer's last cleanup, each thresholdTj=[k>=j] is measured inX. On the exact k0..10 domain, its Boolean ANF uses monomial masks1..10. Only mask7=k0*k1*k2 has degree three, and its coefficient isone exactly for j1,3,5,7. The current forward routine computes g=k0*k1 with one AND, repays all threshold phases using Clifford gates on flags+g, then measuresg with its Clifford correction.

The replacement creates no quantumg. For each measuredTj, apply all linear and quadratic ANF phase terms to the four live count bits. Accumulate the outcomes for j1,3,5,7 into one explicitly zero-initialized classical parity bit. Apply one CCZ to k0,k1,k2 conditioned on that parity. The parity is a nonzero affine combination of four independent HMR outcomes, so its exact probability is1/2. All individual cubic HMR coefficients are then paid. Free the parity after use; it is not a deferred debt.

| Complete component item | Native RN2-B | RN2-D isolated target |
|---|---:|---:|
| Forward prefix/routing arithmetic before final cleanup |51 |51 unchanged |
| Final threshold cleanup |1AND |1 conditionalCCZ=0.5E |
| Forward expected cost |52 |51.5 |
| Unchanged RN2-B inverse |44.5 |44.5 |
| Complete isolated normalization |96.5 |96.0 |
| Forward/inverse HMR variables |21/10 |20/10 |
| Local forward/inverse peaks |46/32 |46/32 |
| External owners |input22+flags4=26 |same26 |
| New phase debt, T, rotations, accuracy change |0 |0 |

The isolated full-circuit delta from frozen candidate08 is-0.5E:1568.0 Toffolis,4T,33R,Q48, expected cost86392.70685415737. If RN2-C independently passes, its43.5E inverse composes with this51.5E forward for a95.0E normalizer, a further1.5E saving from candidate08 and calculated whole cost86344.70685415737. Neither estimate is native or official qualification.

The source extends the pure Boolean proof builder only to expand classical XORs back into independent original HMR symbols. A small positive/negative affine-transcript self-test validates that extension. It then checks the exact normalized output, exponent, restored input, zero scratch and every original HMR coefficient on all3,133,452 inputs. Every charged gate has either no classical condition or a proved nonzero affine condition, so the paper expectation does not assume independence of correlated guards. Native integration, if later authorized, must use the unchanged independent native symbolic checker and exact guard-probability counter.

The frozen source runs under the new strict guard with a30-second timeout and512MiB address cap. This branch is kept separate until its complete symbolic proof passes; a combined95.0E native component needs a new parent gate.
