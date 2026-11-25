# Q880 DQI source candidate

This ZIP contains the complete pinned round12 source snapshot, the previously
built Q881 optimizations, and the latest accepted improvements. It is source
only: no compiled circuit, native library, runtime, or generated test output.

## Current status

**The new combined candidate has not been built or fully verified.** All new
components passed their focused checks. The projected combined resources are
**880 qubits, 906,693 static Toffolis, and 905,912.190673828125 expected Toffolis**.
These are additive component projections, not a measured full-decoder score.

Relative to the previous built Q881 / 929,463-static-Toffoli candidate, the new
patches save **22,770 Toffolis** and are expected to remove one peak qubit.
Relative to the pinned Gluzdov round12 source, the projected saving is58,482T.
The previous Q881 candidate passed reduced full-circuit screens, but its full
verifier was killed by an8GiB memory limit before returning a report. No full
PASS, final measured score, or Kaggle submission is claimed for either candidate.

## New accepted changes

| Change | Whole-decoder Toffoli saving | Other effect |
|---|---:|---|
| Direct gap-polynomial conversion | 20,652 | Conversion peak878, below predicted full peak |
| Odd-code first-gap pointer | 1,396 | Phase peak decreases by one qubit |
| Specialized extraction self-products and compact tail filter | 722 | Lower extraction workspace |
| Exact sparse classical Fourier projection | 0 | Projection operations20,691,162→3,595,172 |

Projected static stage counts are292,686 extraction;62,624 conversion;196,073
phase;62,624 reverse conversion;292,686 reverse extraction. Sum906,693.
The root scan and its execution probabilities are unchanged.

The conversion absorbs two long coherent rotations into a degree-two polynomial
factor. The gap pointer encodes occupied code k as2k−1, exposing its active bit.
Extraction specializes diagonal field products, including a27-Toffoli x^17
map, and reuses or removes temporary words. The classical projection uses a
sparse4095-point mixed-radix DFT with radices3,3,5,7,13; it never stores a
syndrome-derived quantum value in a classical register.

All accepted patches preserve the incumbent's implemented zero-safe arithmetic
and approximation policy. They do not prove decoding correctness on every legal
syndrome. The rejected cache-commutation experiment is excluded from this ZIP.

## Completed component checks

- Conversion: stages8/17/33 with all pending/gap controls and zero words;
  full64-fixture arbitrary-word/history comparison; both old/new inverse
  compositions, including a nontrivial Z/CZ fingerprint; zero errors.
- Encoded phase pointer:22fixtures at degree4 and55at degree17, each in both
  inverse-composition orientations, including weights0–35, subgroups/cosets,
  zero pivots and arbitrary extension inputs; zero errors.
- Extraction:4096inputs for x^17;192selected self-product fixtures;
  128selected filter fixtures;512filter inverse compositions;16combined
  extraction fixtures; zero value, phase or scratch errors.
- Projection:8native fixtures versus the direct field formula, zero errors;
  exact symbolic comparison of all41,277,600binary-map coefficients, zero
  mismatches. Classical work bits are cleared explicitly before being freed.
- Independent source review checked the projection ownership and gap-pointer
  invariants. The main integration build and full verifier remain outstanding.

## Dependencies and build

Use Linux x86-64, CPython3.13 and NumPy. Tested runtime: CPython3.13.17,
NumPy2.5.4. Obtain the official Kickmix native extension separately and place
`kickmix.so` in `decoder/lab/official/kickmix/`. Its expected SHA-256 is:

    c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e

From the extracted root:

```sh
python3.13 build.py
```

This installs the seven production patch entry points in the required order,
builds`build/dqi.kmb`, and writes its resource/stage/hash reports. The three
new extraction helpers must stay beside`extraction_improvements.py`.
All original public source licenses and notices are retained.

## Cheap screening, then one final full verification

```sh
export DQI_WORKSPACE="$PWD"
python3.13 decoder/integration_work/screen_native.py build/dqi.kmb \
  --num-shots 36 --all-weights --zero-sigma1 --output build/all_weights.json
python3.13 decoder/integration_work/screen_native.py build/dqi.kmb \
  --num-shots 256 --output build/distribution.json
python3.13 improvements/root/verify_checkpointed.py build/dqi.kmb \
  --num-shots 102400 --salt quant-fixed-development-v1 \
  --max-workers 4 --output build/full_verification.json
```

The new verification driver passively records completed batches and the
pre-depth aggregate, while requiring the unchanged official`verify()` function
to return before writing a final PASS report. Its tracing and parallel checkpoint
path have been syntax checked but have not yet been exercised on this combined
candidate. It does not change the official functions, locals, inputs, confidence
rule, or seed derivation. The original simple verifier driver is also retained
under`round13/root/verify_final.py`.

Use sufficient RAM for native depth reporting. The reduced classical projection
may help its memory demand, but that has not yet been measured on a full build.
The optional`round13/root/native_tmpdir.c` redirects native temporary-file
placement when the system temporary disk is full; it does not increase RAM.

The preserved`previous_candidate_README.md` describes the earlier built Q881
candidate and its native hash. That hash does not apply to the new candidate.
`SHA256_MANIFEST.json` records every file in this source release.

## Public provenance

- https://www.kaggle.com/datasets/dmitriigluzdov/vqcc-femoco-public-factorization
- https://www.kaggle.com/code/magmacot/qcc-76q-881q-dqi-verified-blend
- https://www.kaggle.com/code/dmitriigluzdov/quantum-circuit-compilation-from-source
