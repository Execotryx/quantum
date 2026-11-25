import sys; sys.path.insert(0,"src")
import numpy as np
from qcompile.dqi.field import GF4096
from qcompile.dqi.tower import tower, linear, parity_map
F=GF4096(); t=tower()
powers=tuple(F.exp[65*i] for i in range(11))
S15=((6, 6, 52), (8, 8, 3), (16, 16, 36), (17, 17, 41), (25, 25, 42), (26, 26, 10), (27, 27, 34), (28, 28, 62), (30, 30, 57), (35, 35, 21), (39, 39, 4), (46, 46, 1), (48, 48, 56), (51, 51, 49), (60, 60, 38))
z=next(v for v in range(2,4096) if v not in set(linear(powers[:6],i) for i in range(64)) and F.exp[(F.log[v]*64)%4095]^v==1)
norm=F.mul(z,z^1); coords=t.coordinates
assert t.quadratic_norm==norm
terms=[]
for mask,_,w6 in S15:
    word=linear(powers[:6],w6)
    for form,scale in ((mask,z^1),(mask<<6,norm),(mask|(mask<<6),z)):
        p=parity_map(coords,form); terms.append((p,p,F.mul(word,scale)))
print("terms",len(terms))
xs=np.arange(4096,dtype=np.uint32)
def par(mask): 
    v=xs & mask; c=np.zeros(4096,dtype=np.uint8)
    for b in range(12): c^=((v>>b)&1).astype(np.uint8)
    return c
exp=np.array(F.exp,dtype=np.uint32); log=np.array(F.log,dtype=np.int64)
ok=True
for x0 in range(0,4096,512):
    X=xs[x0:x0+512][:,None]; Y=xs[None,:]
    acc=np.zeros((512,4096),dtype=np.uint32)
    for a,b,w in terms:
        pa=par(a)[x0:x0+512][:,None]; pb=par(b)[None,:]
        acc^=((pa&pb).astype(np.uint32))*np.uint32(w)
    ref=np.where((X==0)|(Y==0),0,exp[(log[X]+log[Y])%4095])
    if not np.array_equal(acc,ref): ok=False; print("mismatch at block",x0); break
print("exhaustive 4096x4096:", ok)
