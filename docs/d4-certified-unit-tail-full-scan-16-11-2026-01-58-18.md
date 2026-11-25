# D4 certified unit-tail synthesis and scan

The new native probe starts from the exact captured s2 syndrome,
computes its unit-tail certificate, synthesizes both polynomials,
and runs the admitted converter and full projected scan. It uses
the original chart without affine preshear or a second extraction.
The topology and degree-31 padding are fixed to the captured case.
The retained certificate is checked at the synthesis boundary.
A general decoder still needs to select this or a different
valid synthesis route from live inputs.

## Register layout

The last collapsed pair maps the unit tail to `(h,1)`. The circuit
aliases the two numerator coefficients to the live first head and
initializes the constant denominator in one zero second-head word.
Finite inverse pairs grow each polynomial by two slots using their
own head storage. The numerator bank has one more slot than the
denominator bank, which allows the full head products without
clipping their highest terms.

At the middle collapse the first finite absorber uses the substituted
second head of one. It produces `D=U+qV`. The second absorber
produces `qU+hD`. Adding `qD` gives the correct numerator
`hD+q²V`. That shear fits the tight banks because the highest
V word is zero on this collapsed chart, so the highest D word
also vanishes. The two-slot layout used by previous mixed-chart
probes remains supported.

The outer inverse omits the first quadratic and produces the evaluator
`(N+h0D)/q0` with the original locator. The test verifies both
polynomials against independent arithmetic, up to the same nonzero
scale. The converter consumes the normalized locator after padding
with two irreducible quadratics and uses the implicit degree-35
leading coefficient. The probe projects the masks before changing
the syndrome. This lets it reuse the syndrome wires for extraction
and synthesis without another copy.

After scanning, the circuit reverses the conversion, padding,
normalization, all inverse folds, and extraction. The phase comparison
uses the frozen failing mask and a fresh mask at each simulator seed.
It also checks complete restoration of syndrome, mask, and scratch wires.

## Resource decision

The padded circuit restored the expected phase on the captured mask
at both seeds. It used 1,005 qubits and averaged 463,128 and
463,106 executed Toffoli-like gates over the captured and fresh mask
at the two respective seeds. The banked
reference allows about 343,000 gates at 1,005 qubits even at the
minimum priced repetition factor. At the measured gate count,
the width would need to be about 865 qubits to fit the same cost.
The exact path therefore needs substantial gate savings alongside
any register savings before further candidate pricing.

## Degree-31 converter and scan

An unpadded variant uses the locator's actual odd degree. It adapts the
admitted streaming converter's short Hankel kernel and keeps its
measurement-token protocol. It also adapts the projected scan recurrence
to advance the implicit leading term by `alpha^31`. The evaluator and
locator are still normalized before conversion. The raw locator scale
is stored in the unused final second-head word. The unpadded circuit
reclaims the inverse before conversion and offers the now-zero leading
slot to the converter as its history scratch.

The first degree-31 run passed the captured mask and the fresh masks
at 945 qubits and roughly 438,300 executed gates. Removing the extra
registers for degree-35 padding accounted for 60 qubits. Omitting the
four surplus degrees removed about 24,800 gates. At 945 qubits the
banked cost permits about 388,168 gates, so this path also exceeds the
budget before allowing a general chart fallback.
Reusing the leading slot and clearing the inverse before conversion
kept the final circuit at 945 declared qubits. The two local means
were 438,316 and 438,249 gates. That reuse did not reduce the overall
width in the linked probe.

The degree-parametric adapter reuses the SomeJoint D4 converter and
scan algebra from admitted revision
`a4b5a8c288f17f8c09469820848d2d7c16e16044`. The source manifest
identifies the pinned upstream paths and Apache-2.0 licence. Both
the mask projection and the omitted outer factor are unchanged.

[Admitted source manifest](../third_party/dqi-d4/SOURCE.json)
· [Padded cloud test log](evidence/d4-compact-repair-20261115/cloud-unit-tail-full-scan/run.log)

## Cloud verification

All four focused tests in the padded run passed and reproduced the
local counts. Its downloaded receipt archive matched SHA-256
`9043015f386754a5984898740b11f9d80d3848f3b54c301635d655678f3d00b8`.
The separate degree-31 run reproduced both local resource counts
and the restored phase on the archived and fresh masks. Its downloaded
receipt archive matched SHA-256
`a418c50f2d0c9b25980015e1bf6b905789169f98d834bc65f46208c833ea5377`.
Compute Engine confirmed the VM was terminated after both downloads.

[Degree-31 cloud log](evidence/d4-compact-repair-20261115/cloud-unit-tail-degree31/run.log)
· [VM stop receipt](evidence/d4-compact-repair-20261115/cloud-unit-tail-degree31/vm-stop.json)
