# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Exact2^-50-turn mathematical oracle, independent of native endpoint aliases."""
import numpy as np
import variant
from whole_model import phase_units as old_phase_units,MAX_X

MODULUS=1<<50;MASK=np.uint64(MODULUS-1)
DELTA50=tuple(v//16384 for v in variant.BOUND['delta_turn_units64'])
assert all(v%16384==0 for v in variant.BOUND['delta_turn_units64'])
assert tuple((old<<13)+delta for old,delta in zip(variant.COEFFICIENTS37,DELTA50))==variant.NEW_TURN_UNITS50


def phase_units50(xs):
    """Canonical exact phase, checked by independent direct and delta sums."""
    old,chart=old_phase_units(xs,return_chart=True)
    old=np.asarray(old,dtype=np.int64);k=np.asarray(chart['flags'],dtype=np.int64)
    z=old&((1<<27)-1)
    assert np.all((k>=0)&(k<=10)) and np.all((old>=0)&(old<(1<<37)))
    # The endpoint feature identity was proved for every exponent and affine
    # basis word. This recovery additionally checks the endpoint constants.
    p=(z>>k)|((z&((1<<k)-1))<<(27-k))
    assert np.all((p&1)==1) and np.all(((p>>26)&1)==1)
    assert np.array_equal(((p<<k)+(p>>(27-k)))&((1<<37)-1),old)
    direct=np.zeros(len(old),dtype=np.int64);delta=np.zeros(len(old),dtype=np.int64)
    for i in range(34):
        if i<27:feature=(z>>i)&1
        elif i==27:feature=(k==0).astype(np.int64)
        else:
            j=i-27;feature=((z>>j)&1)*(k>j)
        direct+=feature*variant.NEW_TURN_UNITS50[i]
        delta+=feature*DELTA50[i]
    for j in (7,8,9):
        direct+=((z>>j)&1)*(k>j)*(1<<(40+j))
    a=direct.astype(np.uint64)&MASK
    b=((old.astype(np.uint64)<<np.uint64(13))+delta.astype(np.uint64))&MASK
    assert np.array_equal(a,b),'New-angle direct sum differs from old exact phase plus quantized perturbation.'
    return a
