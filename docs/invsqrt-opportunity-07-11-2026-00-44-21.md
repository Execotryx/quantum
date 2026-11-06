# Inverse-square-root opportunity screen

Created 07-11-2026-00-44-21 in Asia/Qyzylorda.

The prospective protocol froze the accepted reference and the two shapes
selected during prior scouting. The earlier scouting result informed the
registration. The recorded screen started after the protocol, harness,
dependency lock, contract, backend inventory and baseline evidence were hashed.

The reference control reproduced the accepted canonical KMB and complete cost
of 2,076,774.233715282. The lead and fallback then ran concurrently on separate
logical CPUs in local Ubuntu WSL with Python 3.13.15. All three arithmetic scans
covered 3,133,452 inputs. Each reloaded circuit was checked on initialized basis
inputs with zero scratch. The checks compared the tracked phase to the model,
restored the input and scratch, and matched sampled executed counts to static
counts. These results cover the registered fixtures and the model's full domain.
The component verifier supplies the separate dynamic full-domain evidence.

| Lane | Modeled cost | Modeled reduction | Minimum margin in phase64 units | Worst tolerance used | Native development trajectories |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reference | 2,076,774.23 | 0% | 332,168,080 | 47.69% | 40,448 |
| Lead | 1,971,483.44 | 5.07% | 102,726,012 | 84.69% | 40,384 |
| Fallback | 1,989,316.54 | 4.21% | 192,802,399 | 78.88% | 40,448 |

The three attempts took 15.39 wall seconds and 12.88 process CPU seconds.
Both candidates qualified. The registered lowest-cost rule selected the lead
with SHA-256 `9816fbfb5544949fb2c448410daf8144b825e45d0105cb118aac75c1a8c910e9`.
All artifacts and receipts are under `runs/invsqrt-opportunity-20261107/`.
The reproduction directory retains exact copies of the registered harness,
protocol and dependency lock.

The implementation reuses the pinned builder, integer targets and native
verifier. It keeps individual attempts in the ledger and ranks qualifying
candidates only after checking the combined budget. The simplicity review
kept screen selection separate from the general candidate state machine.
The performance review kept the exhaustive model chunked and vectorized the
development fixture phase calculation once per circuit. Pyright, Ruff and
strict OpenSpec validation passed before execution.
All 149 existing inverse-square-root and experiment regression tests passed
after confirmation.

## Full verification and fresh confirmation

The pinned inverse-square-root verifier passed 200,540,928 trajectories in each
of two serial runs on the frozen lead KMB. Full verification took 421.66 seconds.
Confirmation was registered after full verification and took 421.19 seconds.
It used a separate salt with the same exhaustive input schedule and official
64 shots per input. The receipt audit verified the run order, distinct salts,
artifact hash before and after execution, and the registered source hashes.

Both runs returned a cost of 1,971,483.438323478, matching the screen estimate.
The measured reduction is 5.0699%. With the other two benchmark costs held
fixed, the geometric aggregate would increase by 1.7494%. Both runs reported
256 qubits, 7,447 Toffolis, one base T operation, and 36 fine rotations per
trajectory. The worst observed tolerance use was 84.6925% at input 2,684,414.
The receipts certify the inverse-square-root component under the pinned local
verifier. Final assembly and full verification of the extracted release ZIP
remain separate.
