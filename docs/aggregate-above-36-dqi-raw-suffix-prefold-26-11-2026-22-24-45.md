# Raw syndrome suffix handoff

The vendored quadratic-node extractor replays previous quotient heads
for each new query. Its source ledger assigns **117,810** charged gates
to query replay for 35 slots in both directions, before scales, inverses,
or synthesis. The following experiment uses a regular Laurent prefix
fraction and keeps the original syndrome suffix at the handoff.
[Vendored extractor and cost ledger](../third_party/dqi-syed-v12/src/src/controller_work/night_c27/arithmetic/raw_query_extractor.py)

Let `B/D` match the first `2k` moments, with `D(0)=1`, and let `Y` be the
raw suffix starting at moment `2k`. The sought prefold is `D*Y + B_shift`,
where `B_shift` is the numerator of the shifted `B/D` sequence. In the
reversed polynomial basis one shift multiplies the numerator by `x`
modulo the locator. A shift by `k` needs a truncated quotient followed
by a truncated product, since the original dividend has a zero low
half. Apply that shift twice, XOR the numerator into the suffix, and
undo the shifts. The four shifts share one reciprocal of the locator
constant. This saves 4,692 explicit ANDs on the degree-35 fixture compared
with computing separate leaf reciprocals.

| Scope | Prefix degree | First-fit software qubits | ANDs per direction |
| --- | ---: | ---: | ---: |
| Degree 3 | 1 | 105 | 498 |
| Degree 35 | 17 | 879 | 28,302 |

Both directions matched direct polynomial multiplication for 12 genuine
syndromes at each size. The replay checked all prefix and suffix words,
phase, and scratch. If the original continued-fraction denominator has
constant `s`, write `E_hat` for the complementary denominator tail scaled
by `s`. The classical fixture verified `B*E_hat = t^(2k-2) mod D` and
checked that `D*G/(1+t²*E_hat*G)` is the sequential residual divided by
`s²`. The circuit still needs to construct the prefix fraction and recover
`E_hat` coherently before it can use that identity in a full decoder.
[Degree-35 replay](evidence/aggregate36-20261126/dqi-raw-suffix-prefold-35.json)

The measured prefold costs **56,604** ANDs round trip. The separate
17-step blocked suffix costs **70,476** products round trip, bringing the
two parts to **127,080** before prefix construction, complementary recovery,
or a complete phase circuit. That exceeds both the strict **2,165.70-gate**
allowance and the **26,149-gate** planning allowance left by the supplied-tape
composition. The E-drive WSL probe remains pending. The highest full cloud
comparison remains **33.20483975**.
[Blocked suffix results](aggregate-above-36-dqi-blocked-suffix-26-11-2026-21-36-16.md)
· [Supplied-tape phase and budget](aggregate-above-36-dqi-borrowed-remainder-26-11-2026-22-13-28.md)
