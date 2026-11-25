"""Cyclic middle-cube interpolation for the T5 Frobenius self-shear.

General cyclic-convolution principle is classical (see the literature
review); unused low/high output coefficients permit fewer Gold evaluations.
An optional single highest-cube correction removes the only overlapping
wraparound coefficient. No approximation or randomized choices are used.
"""
from contextlib import contextmanager
from functools import cache
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import gold_extraction as gold
from gold_forms import linear_form
import jfraction_decoder as jf
from poly_arithmetic import GF, add_scaled
from model_fast_extraction import shear_cost, power_plan
import quadratic_cube
import matrix_pair_kernels

DIVISORS=tuple(n for n in range(1,4096) if 4095%n==0)

@cache
def plan(n,cut):
    old=42*shear_cost(n,2,True,cut)
    best=(old,'original',0,False)
    if n<=3:return best
    whole=26*(3*(cut-2)+1)
    if whole<best[0]:best=(whole,'whole',0,False)
    count=next(q for q in DIVISORS if q>=max(1,n-3,2*cut-3))
    correction=3*(cut-2)>=count and count==2*cut-3
    cost=26*(count+int(correction))
    if cost<best[0]:best=(cost,'cyclic',count,correction)
    return best

def shear(b,source,target,d,cut,*,constant_zero=False):
    n=len(target)
    if not constant_zero or d!=2:
        return gold.ORIGINAL_SHEAR(b,source,target,d,cut,constant_zero=constant_zero)
    cost,method,count,correction=plan(n,cut)
    if method=='original':
        return gold.ORIGINAL_SHEAR(b,source,target,d,cut,constant_zero=True)
    if method=='whole':
        return gold.shear(b,source,target,d,cut,constant_zero=True)
    assert all(source[i] is target[i] for i in range(cut))
    operands=list(source[1:cut])
    indices=list(range(max(cut,3),n))
    outputs=[target[k] for k in indices]
    omega=GF.pow(GF.primitive_element,4095//count)
    for j in range(count):
        point=GF.pow(omega,j)
        weights=[GF.pow(omega,(-j*(k-3))%count) for k in indices]
        with linear_form(b,operands,[GF.pow(point,i) for i in range(len(operands))]) as value:
            assert not isinstance(value,int)
            gold.cube_vector(b,value,outputs,weights)
    if correction:
        assert 3*(cut-2)-count==cut-3
        gold.gold_cube.xor_cube(b.native,source[cut-1],target[cut])
    for i in range(1,(n-1)//2+1):
        if cut<=2*i<n:add_scaled(b,source[i],target[2*i],frobenius=2)

@contextmanager
def installed():
    previous_shear,previous_cube=jf.shear,quadratic_cube.xor_cube
    jf.shear=shear
    quadratic_cube.xor_cube=lambda b,s,t:gold.gold_cube.xor_cube(b.native,s,t)
    try:yield
    finally:jf.shear,quadratic_cube.xor_cube=previous_shear,previous_cube

def extract(b,words,bank,*,reverse=False):
    matrix_pair_kernels.BORROW_ZERO_META=True
    with installed():
        matrix_pair_kernels.extract_hybrid(b,words,bank,reverse=reverse,
                                          fused=True,matrix_threshold=14)

@cache
def power_count(n):
    if n<=2:return (0,0,())
    _,cut=power_plan(n,2)
    old=42*shear_cost(n,2,True,cut)
    new,method,size,correction=plan(n,cut)
    child=power_count(cut)
    row=dict(n=n,m=cut,baseline=old,new=new,method=method,
             cyclic_size=size,highest_cube_correction=correction)
    return (child[0]+old,child[1]+new,child[2]+(row,))

def main():
    lengths=list(range(68,11,-4))+[10,8,6,4,2]
    rows=[]
    for n in lengths:
        old,new,nodes=power_count(n-1)
        rows.append(dict(length=n,baseline=old,new=new,saving=old-new,nodes=nodes))
    out=dict(scope='resource-only cyclic Gold self-shear screen',divisors=DIVISORS,
             rows=rows,roundtrip_saving=2*sum(r['saving'] for r in rows))
    (HERE/'cyclic-gold-count.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
