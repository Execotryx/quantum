# D4 paired extraction and synthesis

The derived emitter now carries the local chart bits coherently, evaluates
the regular or pole recurrence on the external jets, and reverses the same
recurrence while repaying the normalization measurements. The native
[extraction transcript](evidence/d4-extraction-repair-20261115/paired-extraction.json)
agreed with the independent
[rational comparison](evidence/d4-extraction-repair-20261115/paired-extraction-compare.json)
on all eight focused shots. In s2 shot 45440 it retained the group 6 local
pole and matched the rational continuation through termination at head 32.
The inverse restored the original syndrome, scratch and phase over 1,024 shots.

The scalar tail at zero is evaluated by the same paired recurrence. The
native two-bank reconstruction with 36 coefficients per bank and a
one-sided linear tail produced the exact BM/Forney symbols on all eight
focused inputs, including the genuine local pole. The reconstruction and
its inverse restored syndrome, scratch and phase across 1,024 shots without
the residue scan. The measured closed diagnostic used 1,781 qubits and
1,546,553 static Toffoli-like gates.
[Coefficient evidence](evidence/d4-extraction-repair-20261115/paired-synthesis.json)
· [Exact support and symbol cross-check](evidence/d4-extraction-repair-20261115/paired-synthesis-compare.json)

The one-sided linear seed does not cover full verifier inputs. Ordinary
weight-35 samples reach a quadratic numerator over a linear denominator.
The classical implementation recovers those tail coefficients from the
projective jet and the full degree bounds. It solves the resulting field
equations and reports singular or inconsistent cases. The remaining
circuit work is to derive and emit the reversible tail recovery and cover
any higher-degree or singular input charts before freezing an official
candidate. The 36-coefficient reconstruction is a local diagnostic and
provides no full-domain or cloud acceptance claim.

The [focused native scan](evidence/d4-extraction-repair-20261115/paired-focused-scan.json)
applied the phase on the 235 points in the union of the eight fixed
supports. All eight phases matched their original expected values. All
1,024 shots restored syndrome, mask and scratch. The closed diagnostic
used 1,817 qubits and 1,587,443 static Toffoli-like gates. The separate
full-field algebraic comparison checked all 4,095 possible roots of each
of the eight synthesized denominators. Together they cover the known
failures without certifying the proposed general emitter.

For the normal chart at full weight, let the tail be
`N_t=n0+n1*X+n2*X²`, `D_t=d0+d1*X`. The native jet gives
`L=n1*d0+n0*d1`. Apply the homogeneous pair folds to the three unknown
coefficient columns and the known constants. The original numerator has
degree at most 34 and the denominator at most 35. With all regular
charts, the two high numerator coefficients at degrees 35 and 36
provide the other two equations. A coherent three-by-three solver now
implements the arithmetic on supplied columns and retains a singular
predicate. The matrix-column emission from live heads and the degree
checks for pole charts remain to be integrated. This work precedes the
full-grid build and three-hour verifier campaign.
