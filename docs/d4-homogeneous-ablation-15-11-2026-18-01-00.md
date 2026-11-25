# D4 homogeneous extraction ablation

Routing groups 6 and 7 through D4's existing homogeneous recurrence
restored every true denominator root on three failed shots. The
[matched native check](evidence/d4-extraction-repair-20261115/matched.json)
confirmed the three phase corrections over 1,024 shots, with zero new
value, mask or scratch errors and no new phase errors. The s2 phase error
at shot 45440 reproduced unchanged. Its local inverse still gets zero
after the first finite head.

| Circuit | Qubits | Static Toffoli-like gates |
| --- | ---: | ---: |
| Banked D4 | 897 | 444,667 |
| Groups 6 and 7 homogeneous | 899 | 443,969 |

The exact doubled-node transfer now has a classical implementation and
an inverse. Its homogeneous derivative update avoids division by the
next denominator, including when that denominator is zero. Eight
[constructed inputs](evidence/d4-extraction-repair-20261115/exact-pole-fixtures.json)
exercise the first local pole and intermediate poles in groups 1–7.
The ordinary extractor has no intermediate updates in group 0.

The expanded route for groups 1–7 has 904 qubits and 444,989 static
Toffoli-like gates. It reproduced the same three corrections and left
only the s2 phase error in the
[matched historical batches](evidence/d4-extraction-repair-20261115/homogeneous-1-7-matched.json).
For the eight constructed inputs, the expanded route passed all 32
input-mask combinations under each of two simulator seeds. Banked D4
produced five phase errors under each seed. All runs restored the values,
masks and scratch. [Constructed-input results](evidence/d4-extraction-repair-20261115/fixture-replay.json)

The native homogeneous transfer primitive matched the independent
extension-field model on 64 inputs under two simulator seeds, including
a state whose next denominator vanishes. Its inverse restored every
input. The full decoder still needs coherent local-chart selection and
integration with synthesis and its inverse.
