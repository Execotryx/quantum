# Q881 DQI decoder source

This source-only package contains the pinned Gluzdov round12 source snapshot,
three local optimization modules, the build driver, the unchanged official
verifier source, and a reduced native-screen driver. It contains no compiled
circuit, native binary, Python runtime, or generated test reports.

## Candidate status

The combined candidate was built at 881 qubits and 929,463 static Toffolis.
Its exact expected count is 928,682.190673828125, a reduction of 35,712 from
the pinned round12 implementation. The built candidate passed a 36-fixture
all-weight screen with forced zero first locator coefficients and a separate
256-fixture official-distribution screen, with zero value or phase errors.

A completed full official verifier report is NOT available. The final run
was killed by the workspace's 8 GiB memory limit before returning its report.
The earlier attempt failed before sampling because the system temporary disk
was full. No official PASS, measured full-run score, or submission is claimed.
The native depth-reporting calculation is the suspected memory bottleneck.

These are exact replacements of the incumbent arithmetic, including its
zero-safe extensions. They preserve its approximation policy and do not claim
correct decoding on every legal syndrome.

## Changes

- `round13/phase/top_quotient.py`: top-first quotient interpolation,
  saving 20,160 Toffolis over the forward and reverse phase transforms.
- `round13/conversion/banded_conversion.py`: degree-one interpolation in
  polynomial conversion, saving 11,904 Toffolis over both directions.
- `round13/extraction/norm_guard_scaling.py`: use the existing six-bit norm
  for zero guards in 304 scalar caches, saving 3,648 Toffolis.

The combined stage counts are 293,047 for extraction, 72,950 for conversion,
197,469 for the phase, 72,950 for reverse conversion, and 293,047 for reverse
extraction. Peak width remains 881. Additional linear arithmetic increases
the total recorded instruction count from 83,982,929 to 91,200,171.

## Dependencies

Use Linux x86-64 with compatible CPython 3.13 and NumPy. The tested versions
were CPython 3.13.17 and NumPy 2.5.4. Obtain the official Kickmix native
extension separately and put `kickmix.so` in `decoder/lab/official/kickmix/`.
It is omitted because this package is source only. The expected extension SHA-256 is:

    c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e

The original public source licenses and native-backend license are retained.
A machine with more memory than the 8 GiB research workspace is recommended
for the complete official verifier, particularly its native depth calculation.

## Build

Run from the extracted package root, preserving its directory structure:

```sh
export DQI_WORKSPACE="$PWD"
export PYTHONDONTWRITEBYTECODE=1
python3.13 round13/root/build_candidate.py \
  --patch round13/extraction/norm_guard_scaling.py \
  --patch round13/phase/top_quotient.py \
  --patch round13/conversion/banded_conversion.py \
  --output build/dqi.kmb
```

The driver records the original recipe, patch hashes, stage counts, and
native output hash. The expected candidate SHA-256 is:

    ea2c00e071dbb5ae2de55eb1cc35d5e03e209038cb47888e1e9f85f953e93f1a

The output is 869,645,922 bytes. The pinned baseline SHA-256 is:

    835414f51eff796282be942f86e0f479901597c144481653eed63402cb6e4ea0

## Screen, then verify fully

```sh
python3.13 decoder/integration_work/screen_native.py build/dqi.kmb \
  --num-shots 36 --all-weights --zero-sigma1 --output build/all_weights.json
python3.13 decoder/integration_work/screen_native.py build/dqi.kmb \
  --num-shots 256 --output build/distribution.json
python3.13 round13/root/verify_final.py build/dqi.kmb \
  --num-shots 102400 --salt quant-fixed-development-v1 \
  --output build/full_verification.json
```

The final driver uses the unchanged official verifier, one worker, and no
explicit seed override. Its verifier-source pin is:

    f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65

The native serializer uses libc `tmpfile64`, which can ignore `TMPDIR`.
If the system temporary volume is full, the optional `native_tmpdir.c` source
redirects only temporary-file placement. Compile it with
`cc -shared -fPIC -O2`, then set `LD_PRELOAD` to the resulting absolute library
path and `DQI_NATIVE_TMPDIR` to an absolute directory with sufficient free
space. The redirected serializer was checked to preserve the candidate bytes
and SHA-256. This workaround does not address a memory limit when the chosen
temporary directory is memory-backed.

## Provenance

The public source snapshot contains 131 files from dataset version 9; its
selected DQI recipe rebuilds the historical round12 artifact. The source
manifest and original license/notice files are included.

- https://www.kaggle.com/datasets/dmitriigluzdov/vqcc-femoco-public-factorization
- https://www.kaggle.com/code/magmacot/qcc-76q-881q-dqi-verified-blend
- https://www.kaggle.com/code/dmitriigluzdov/quantum-circuit-compilation-from-source
