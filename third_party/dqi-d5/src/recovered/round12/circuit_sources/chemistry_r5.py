# SPDX-License-Identifier: Apache-2.0
"""Own R1/B496 numeric factors, arbitrary C; exact b11/J10/anf0 rebuild.
Modified round9: permit ensemble compression; QROM construction unchanged.

ANF/erasure: Artem Nazemtsev. Pebbling/signed gauge: Kozykorpesh.
D-penalty and sensitivity quantization lineage: Ahmed Berat Ozer.
"""
from functools import lru_cache
from pathlib import Path
import math, shutil
import numpy as np
import kickmix as km
from dfthcsos.scoreinfra import dfthc_math as M
def pack(row, brot):
    return sum(int(value) << (j * brot) for j, value in enumerate(row))

def mobius_transform(table):
    """Packed-output Boolean truth table <-> ANF coefficient table over GF(2)."""
    result = list(map(int, table))
    if not result or len(result) & (len(result) - 1):
        raise ValueError("truth-table length must be a power of two")
    n = (len(result) - 1).bit_length()
    for bit in range(n):
        step = 1 << bit
        for start in range(0, len(result), 2 * step):
            for offset in range(step):
                result[start + step + offset] ^= result[start + offset]
    return result
def xor_and(b,left,right,targets):
    targets=list(targets)
    if not targets:return
    q=targets[0]
    for t in targets[1:]:b.cx(q,t)
    b.ccx(left,right,q)
    for t in reversed(targets[1:]):b.cx(q,t)

def pebbled_init(b,table,address,outputs,scratch):
    address,outputs,scratch=map(list,(address,outputs,scratch))
    H,n=len(table),len(address)
    coefficients=mobius_transform(list(table)+[0]*((1<<n)-H))
    coefficients[H:]=[0]*((1<<n)-H)
    completed=mobius_transform(coefficients)
    assert completed[:H]==table
    stats={'monomial_ands':0,'recomputed_ands':0,'pebble_sites':0,'direct_leaf_ands':0,'scratch':len(scratch)}
    @lru_cache(None)
    def children(mask,last):return tuple((mask|(1<<j),j) for j in range(last+1,n) if (mask|(1<<j))<H)
    @lru_cache(None)
    def need(mask,last):
        return max([1+need(c,j) for c,j in children(mask,last) if children(c,j)]+[0])
    def targets(mask):
        v=coefficients[mask]
        return [outputs[j] for j in range(len(outputs)) if (v>>j)&1]
    def walk(mask,last,control,path,free):
        erased=[]
        if mask.bit_count()==5 and need(mask,last)>len(free):
            m=need(mask,last)-len(free)
            assert 0<m<=len(path)-1
            erased=path[:m]
            for a,c,t in reversed(erased):b.del_and(a,c,t);free.append(t)
            stats['pebble_sites']+=1
        ts=targets(mask)
        if ts:
            if control is None:b.x(km.array(ts))
            else:b.cx(control,km.array(ts))
        for child,j in children(mask,last):
            if not mask:
                walk(child,j,address[j],path,free)
            elif not children(child,j):
                ts=targets(child)
                if ts:xor_and(b,control,address[j],ts);stats['direct_leaf_ands']+=1
            else:
                assert free,('scratch exhausted',mask,j,len(path))
                t=free.pop();b.init_and(control,address[j],t);stats['monomial_ands']+=1
                walk(child,j,t,path+[(control,address[j],t)],free)
                b.del_and(control,address[j],t);free.append(t)
        for a,c,t in erased:
            free.remove(t);b.init_and(a,c,t);stats['recomputed_ands']+=1
    walk(0,-1,None,[],scratch.copy())
    return completed,stats
def gauge_vectors(u,edges,brot):
    a=np.array(u,dtype=float,copy=True);angles=np.empty((len(u),len(edges)))
    for j,(p,q) in reversed(list(enumerate(edges))):
        norm=np.hypot(a[:,p],a[:,q])
        sign=np.where(abs(a[:,p])<1e-12,np.where(a[:,q]>0,-1.,1.),np.where(a[:,p]<0,-1.,1.))
        angles[:,j]=np.where(norm<1e-12,0.,np.arctan2(a[:,q]*sign,a[:,p]*sign)/np.pi)
        a[:,p]=np.where(norm<1e-12,0.,norm*sign);a[:,q]=0.
    # +pi/2 is the same projective row gauge as -pi/2. Clipping never changes
    # a non-boundary angle; the canonicalization check measures row-sign drift.
    scale=1<<(brot-1)
    integers=np.floor(angles*scale+.5).astype(np.int64)
    integers=np.where(integers==scale//2,-scale//2,integers)
    return integers%(1<<brot)

def canonical_words(words,edges,brot):
    u=M.reconstruct_u_vectors(words/(1<<(brot-1)),edges)
    result=gauge_vectors(u,edges,brot)
    decoded=M.reconstruct_u_vectors(result/(1<<(brot-1)),edges)
    signs=np.where(np.sum(u*decoded,axis=1)<0,-1,1)
    drift=float(np.max(abs(u-decoded*signs[:,None])))
    assert drift<1e-11,drift
    assert not np.any(((result>>(brot-1))^(result>>(brot-2)))&1)
    return result,dict(max_component_drift_up_to_sign=drift,redundant_top_bit=True)
def deltas(words,J):
    A,N=words.shape; K=math.ceil(N/J)
    p=np.zeros((A,K*J),dtype=np.int64); p[:,:N]=words
    batches=p.reshape(A,K,J).transpose(1,0,2); d=batches.copy(); d[1:]^=batches[:-1]
    return d

def qrom_anf0(delta, brot=11):
    A,J=delta.shape; n=(A-1).bit_length()
    assert not np.any(((delta>>(brot-1))^(delta>>(brot-2)))&1)
    values=[pack(row,brot) for row in delta]
    b=km.CircuitBuilder();sel=b.create_quantum_register(n,'selection')
    tgt=[q for j in range(J) for q in b.create_quantum_register(brot,f'word_{j}')]
    # Preserve even zero-sized allocation/free calls from accepted qrom_anf(k=0).
    bank=list(b.alloc_qubits(0));work=b.alloc_qubits(max(1,n-2))
    pebbled_init(b,values,sel,tgt+bank,work);b.free(work)
    b.free(km.array(bank));return b.finish_circuit()

def build_dfthcsos(out, data_file):
    out=Path(out)/'dfthcsos';out.mkdir(parents=True,exist_ok=True)
    with np.load(data_file,allow_pickle=False) as z:
        words,edges=z['angle_words'],z['tree_edges']
        assert z['W'].shape[:2]==(1,496),z['W'].shape
    words,proof=canonical_words(words,edges,11)
    shutil.copyfile(data_file,out/'submission.npz')
    for k,delta in enumerate(deltas(words,10)):
        c=qrom_anf0(delta);assert c.num_qubits<=128
        c.to_file(str(out/f'angle_k_{k}.kmb'),format='kmb')
    assert k==7
    return out
