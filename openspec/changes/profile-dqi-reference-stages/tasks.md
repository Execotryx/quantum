## 1. Proxy and stage map

- [x] 1.1 Implement `StageProfileBuilder` in `tools/dqi_stage_profile.py`. Reproduce the reference KMB hash through the proxy.
- [x] 1.2 Register the stage map from the pinned `ProosAndZalkaDecoder` methods. Fail the run on any unmapped emitting frame.
- [x] 1.3 Read the verifier's Toffoli-like gate definition and use it for counting.

## 2. Measurements

- [x] 2.1 Profile `(63, 4)` and `(127, 12)` on WSL. Check that per-stage sums equal the static total.
- [x] 2.2 Profile `(4095, 70)` on the cloud VM. Record peak process-tree PSS and wall time.
- [x] 2.3 Reconcile the static total with the verifier mean from the matched 2,560-shot control.

## 3. Reports

- [x] 3.1 Write `stage-profile.json` and the product-site census. Explain the 5.09% tower result from the census.
- [x] 3.2 Record declared versus traced peak width.
- [x] 3.3 Write the decision record and the projected costs that set the build order.
- [x] 3.4 Strict OpenSpec validation and a dated change log.

[Measured stage profile and build-order decision](../../../docs/dqi-full-stage-profile-08-11-2026-14-36-03.md)
