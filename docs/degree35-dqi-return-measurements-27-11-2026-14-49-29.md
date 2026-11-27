# DQI return-stage measurement screens for score 35

The guard-aware single-wire screen found **zero** CCXs followed by an
unguarded X-basis measurement where the target was written only by
unguarded CX or CCX gates between those operations. It counted **102,744**
unguarded CCXs and **18,460** unguarded HMR instructions in the pinned
Tony Li source. The earlier fusion tally of **107,045** used absence of an
inline condition and included **4,301** CCXs under nested guard scopes.
That earlier zero-fusion result covers the larger screened set. The raw
fusion receipt preserves its original schema and bytes.
[Measurement screen result](evidence/aggregate36-20261126/dqi-return-measurement-cloud.json)
· [Pair-fusion result](degree35-dqi-return-fusion-screen-27-11-2026-05-32-47.md)

The project worker started, but cloud-init reported `No space left on
device` and its SSH port was unreachable. The screens use Google Cloud
Shell's managed Linux VM with Python 3.12.3. They need the Python standard
library and the hash-pinned KMX source. Neither calls the native verifier.
The project worker was shut down without removing its retained files.
[Google Cloud Shell environment](https://docs.cloud.google.com/shell/docs/how-cloud-shell-works)

The proposed single-wire rewrite advances the original HMR into a fresh
classical bit. Each eliminated target write pays the corresponding phase
at its original position, using the live controls at that position. The
original measurement bit is copied back at its original write. A source
candidate would have to preserve guards and classical outcome order or
prove equivalence under explicitly mapped outcomes.

Astra found an exact example of measurement transport in the first 14
instructions of the source. Thirteen CNOTs preceding `HMR q871 b49140`
transport that measurement's X observable back to wires 144, 223, 632,
784, 861, 871, and 895. Those CNOTs carry no Toffoli charge. The larger
screen tracks the entire subspace of displacements that can vanish under
measurements through unguarded affine operations. It counts a CCX when
its target direction belongs to that subspace and optimistically omits
the gate. Skipping that gate before processing earlier ones allows
cascading deletions in the ceiling. The other CCXs constrain both control
displacements to zero. Guards and other operations end the frame. This
model grants phase repair for free and requires unchanged surviving
values. It does not price corrections or exploit input-specific
identities. Any emitted candidate would need a measurement-outcome map
that respects the original guards and reused classical destinations.
[Screen driver](../tools/dqi_return_bank_screen.py)
· [Measurement-based uncomputation research](degree35-dqi-berlekamp-massey-research-27-11-2026-05-37-57.md)

The broader cloud screen traversed **19,804,589** instructions, reached a
displacement-space dimension of **60**, and still found **zero** deletable
CCXs in its fenced model. Both cloud tests passed. The first compared 512
deterministic operations with explicit displacement sets. The second
covered multiwire transport, cascading deletion, and guard and phase
boundaries. The earlier pair-fusion and both measurement screens now rule
out their respective return-only rewrites within the tested boundaries.
The next source hypothesis needs to alter the representation of live
intermediates or use a proved dependency through a guarded or nonlinear
region. Neither screen emitted a candidate or changed a portfolio score.
[Measured-bank result](evidence/aggregate36-20261126/dqi-return-bank-cloud.json)
· [Invariant tests](../tests/test_dqi_return_bank_screen.py)

At the projected companion costs of **58,000** for inverse square root
and **230M** for chemistry, the 900-qubit DQI budget permits about
**308,602** executed gates with zero verifier failures. The pinned source
uses approximately **316,131**, a gap of **7,529**. With the observed
companion controls of **61,696.17** and **249.132M**, DQI would instead
need a cost at or below **258.440B**, about **267,835** executed gates at
900 qubits under the same zero-failure pricing. Keeping the present gate
count would require at most **828** qubits, below the 840-qubit syndrome
register. Both calculations are component targets. The best complete
cloud comparison remains **33.20483975**.
[Joint budget and exact cost formula](degree35-joint-cost-screen-27-11-2026-04-37-37.md)
· [Inverse control cost](evidence/aggregate36-20261126/invsqrt-checkpoint-return-control-native.json)
· [Complete cloud comparison](above-34-cloud-reference-comparison-26-11-2026-06-31-00.md)
