# Native D4 extraction diagnosis

The instrumented rebuild reproduced banked D4 byte for byte. Four original
batches were regenerated from their official seeds and checked against the
captured inputs. The native extraction words for all eight fixed shots
matched the scalar ordinary-chain model across groups 0–7.

| Draw and shot | First divergence |
| --- | --- |
| s2 / 45440 | Genuine local pole at head 13. The native second head is zero. |
| s6 / 13238 | Group 6, head 12 differs from the rational oracle. |
| s6 / 74119 | Group 7, head 14 differs from the rational oracle. |
| s7 / 46728 | Group 6, head 12 differs from the rational oracle. |

The passing controls agreed with the rational oracle through the external
heads. The companion arithmetic implements the exact split and inverse
for the doubled-node pole branch. On the s2 fixture the continuation
has numerator degree 19 and denominator degree 16, and reconstructs the
original rational pair exactly. The circuit still needs this transfer
wired into extraction and synthesis.

[Native observations](evidence/d4-extraction-repair-20261115/profile.json) ·
[Scalar and rational comparison](evidence/d4-extraction-repair-20261115/oracle.json)
