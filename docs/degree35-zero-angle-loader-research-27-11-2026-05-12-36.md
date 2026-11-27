# Zero-angle assignments in seven-bit chemistry loaders

The v221 control has 2,400 angle words whose Givens rotation acts on two exactly zero coordinates. The ordered tree visits each child for the first time at its rotation. For seven-bit word `w`, a nonzero parent is retained except when `w mod 64` is 32, and the child is populated except when `w mod 64` is zero. When the parent is already zero, any word preserves both coordinates. The cloud screen propagated this support on all 1,219 rows of the hash-pinned factorization. [Screen source](../tools/chem_zero_angle_words.py) · [Cloud receipt](evidence/aggregate36-20261126/chem-v221-zero-angle-cloud.json)

| Assignment on free cells | Words changed | XOR bit toggles | Sum of mixed ranks | Official decoded accuracy |
| --- | ---: | ---: | ---: | --- |
| Original | 0 | 320,222 | 5,805 | Pass |
| Zero | 2,370 | 318,761 | 7,006 | Pass |
| Previous packet on the same lane | 2,360 | 311,779 | 6,741 | Pass |
| Next packet on the same lane | 2,370 | 312,675 | 6,758 | Pass |

The largest observed vector change was 3.47 × 10⁻¹⁶, and effective normalization stayed at 46.9142656241. Every modified packet had mixed rank at or above its original rank. The previous-packet fill removed 8,443 bit toggles while adding 936 to the mixed-rank sum. The mixed ranks and toggle counts are synthesis proxies. The cloud run screened decoded words and emitted no loader circuit for these assignments. The original control appears to preserve useful Boolean structure. Whether this was an explicit objective of the original compiler remains unverified. [Original public assembly and cap](degree35-joint-cost-screen-27-11-2026-04-37-37.md)

## Exact product deletion in a fixed loader decomposition

Astra proposed a narrower linear feasibility test with a direct static gate-count interpretation. Start at the final five-word loader, with 285 free words and no successor transition. Freeze its input packet, carrier endpoints, cache schedule and emitted product controls. Each product then represents one known Boolean truth column over the 1,219 addresses. Delete one column at a time and solve for fan-out coefficients of the remaining columns, the available pure high- and low-address functions, and the constant. Keep the fixed word bits on every constrained address. Retain the carrier parities on both endpoints and route the update only through noncarrier outputs.

The previously replayed slot 14 KMB matches the v221 slot byte-for-byte. It is goodpjw2008's version 21 loader from family `2480d9969c9d`, with **206** static Toffoli-like gates. The permanent endpoint receipt binds its KMX and KMB hashes. Use those bytes to recover the control conditions and distinguish charged products, cache operations, and measurement phase repairs before constructing the equations. [Exact slot receipt](evidence/aggregate36-20261126/chem-affine-endpoints-screen.json) · [Publisher's loader](https://www.kaggle.com/code/goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25564)

The constraints for a fixed deletion are linear over GF(2). If every single deletion is inconsistent, any larger deletion is also inconsistent for the same frozen product dictionary. A feasible deletion identifies a static saving at that decomposition. Its emitted circuit must still load the correct constrained bits, preserve the decoded vectors and restore the reverse endpoint. Compare the actual charged count with the same slot in the current v221 assembly. For an interior packet, solve its incoming and outgoing XOR transitions together with one shared packet value. [Prior endpoint verification](degree35-chemistry-affine-27-11-2026-01-27-18.md)
