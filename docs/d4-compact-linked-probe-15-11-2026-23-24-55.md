# D4 coefficient recovery and linked stage probe

The coefficient audit propagated the exact degree constraints of the
original rational pair through the heads on all 17 doubled nodes.
It covered 44 inputs, including the captured failures and controls,
forced weight-34 and weight-35 poles, and deterministic controls.

The constraints recovered every omitted coefficient on these inputs.
Groups 0–15 had rank at least five, and the final tail varied between
rank three and five. The identity of the fifth high slot changed at
some incoming poles. Only two eliminated words at the projected outer
boundary were uniformly zero. Groups 1–13 shared one such word, and
groups 14–16 shared none. Some recovery recipes need 16 product terms.
The discarded values would therefore need a coherent recipe to avoid
keeping their words live.

The 44-case audit uses the 76-word layout. A separate construction
fixes several finite heads and imposes exact local-pole congruences
on a weight-35 numerator while retaining a valid split locator.
The syndrome and its decoded support match for all three witnesses.
Consecutive poles at groups 0 and 1 used 76 raw words and a rank-five
tail. Separated poles at groups 0 and 2 needed 78 words and rank
seven. Groups 0, 2, and 4 needed 80 words and rank nine. The rank
solver recovers all three using the chart-dependent tail envelope.
The fixed 76-word native ladder lacks capacity for the last two
witnesses.

The native probe linked both stages on 15 inputs. It checked the
extracted heads, chart flags and projective tail against the data supplied
to the complete 17-node synthesis ladder. The ladder emitted the exact
locator and evaluator. The banked converter and projected scan restored
syndrome, masks, heads, chart bits and scratch. The phase matched the
captured masks and a second independently varied mask set.
The Google Cloud run passed the same probe and produced a byte-identical
report. The downloaded receipt archive matched SHA-256
`082c086caf962db9953e267558e3be17f2d0aaf42c9b73a7469d03c24cf487b1`.
The stop command lost its response, and a separate Compute Engine
status query confirmed the VM was terminated.

The probe supplied the tail polynomial coefficients and a classical
padding selection. It used a separate 840-qubit copy for the original
syndrome at mask projection. This exercises the phase path across all
folds and gives measured resource evidence for the two stages. It does
not implement a coherent tail and padding handoff.

The two stage means add to 478,201.53 and 478,205.80 executed
Toffoli-like gates across the two simulator seeds. At the synthesis
ladder width of 993 qubits, the banked reference price allows about
351,549 gates per shot. If coefficient reclamation were free and reduced
synthesis below the measured extraction width of 944 qubits, that width
would still allow only about 388,991 gates. The current arithmetic
schedule falls outside the budget on these fixtures before charging
coherent tail or padding work.

[Coefficient recovery audit](evidence/d4-compact-repair-20261115/coefficient-recovery-audit.json)
· [Multiple-pole witnesses](evidence/d4-compact-repair-20261115/multiple-poles.json)
· [Local linked probe](evidence/d4-compact-repair-20261115/linked-synthesis-probe.json)
· [Cloud linked probe](evidence/d4-compact-repair-20261115/cloud-linked/report.json)
· [VM stop](evidence/d4-compact-repair-20261115/cloud-linked/vm-stop.json)
