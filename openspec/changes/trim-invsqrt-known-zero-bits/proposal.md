## Why

The certified 28/20/14 lattice table never sets the high bit of its declared
coefficient registers. Its output integer bit is also zero over the verifier
domain. An opt-in implementation removes these bits and reduces row workspace.

## What Changes

- Preserve the certified control and table, and validate every table word fits
  its narrower register.
- Check every forward Horner subtraction and output shift over the full domain,
  and compare phase words byte-for-byte with the frozen control model.
- Price the width change before emission, check native phase and cleanup, and
  rebuild identical KMB bytes independently.
- Register a separate successor before full verification, fresh one-use
  confirmation and any paired archive verification.

## Impact

Development candidate `f4c8503d...a70fb200d` has measured cost 472,336.92,
7.29% below the certified 509,471.48 control. This is development evidence,
not a completed confirmation or release claim.
