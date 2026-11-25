"""T5 adjunct: checked26-AND cubes in whole self-shear interpolation.

This is a structural arithmetic specialization, but its measured task-level
opportunity is only about0.5%; it is not claimed as an independent Tier1 win.
The old R24 planner/evaluation algebra remains credited in upstream/NOTICE.
New field tensor is the field agent's checked GF4-Hermitian construction.
"""
from contextlib import contextmanager
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'gold26'),str(HERE)]
import runtime
import gold_cube
from gold_forms import linear_form
import jfraction_decoder as jf
from poly_arithmetic import GF, add_scaled, interpolation_columns
from model_fast_extraction import shear_cost
import quadratic_cube
import matrix_pair_kernels

ORIGINAL_SHEAR=jf.shear
ORIGINAL_CUBE=quadratic_cube.xor_cube

def cube_vector(b,source,targets,coefficients):
    live=[(w,c) for w,c in zip(targets,coefficients) if w is not None and c]
    if not live:return 0
    pivot,scale=live[0]
    others=[(w,GF.div(c,scale)) for w,c in live[1:]]
    for w,c in others:add_scaled(b,pivot,w,c)
    if scale!=1:b.gf2_idiv(scale,target=pivot,field=GF)
    gold_cube.xor_cube(b.native,source,pivot)
    if scale!=1:b.gf2_imul(scale,target=pivot,field=GF)
    for w,c in reversed(others):add_scaled(b,pivot,w,c)
    return 1

def shear(b,source,target,d,cut,*,constant_zero=False):
    n=len(target)
    evaluations=3*(cut-2)+1 if n>3 else 0
    eligible=(constant_zero and d==2 and n>3 and
              26*evaluations<42*shear_cost(n,d,True,cut))
    if not eligible:
        return ORIGINAL_SHEAR(b,source,target,d,cut,constant_zero=constant_zero)
    assert all(source[i] is target[i] for i in range(cut))
    # A=1+xG: the nonlinear self increment is x^3 G^3. The remaining
    # x^(2i)*a_i^2 terms are GF2-linear and emitted separately below.
    operands=list(source[1:cut])
    outputs=[target[k+3] if cut<=k+3<n else None for k in range(evaluations)]
    for point,column in enumerate(interpolation_columns(evaluations)):
        if not any(w is not None and c for w,c in zip(outputs,column)):continue
        with linear_form(b,operands,[GF.pow(point,i) for i in range(len(operands))]) as value:
            assert not isinstance(value,int)
            cube_vector(b,value,outputs,column)
    for i in range(1,(n-1)//2+1):
        if cut<=2*i<n:add_scaled(b,source[i],target[2*i],frobenius=2)

@contextmanager
def installed():
    previous_shear,previous_cube=jf.shear,quadratic_cube.xor_cube
    jf.shear=shear
    quadratic_cube.xor_cube=lambda b,s,t:gold_cube.xor_cube(b.native,s,t)
    try:yield
    finally:jf.shear,quadratic_cube.xor_cube=previous_shear,previous_cube

def extract(b,words,bank,*,reverse=False):
    matrix_pair_kernels.BORROW_ZERO_META=True
    with installed():
        matrix_pair_kernels.extract_hybrid(b,words,bank,reverse=reverse,
                                          fused=True,matrix_threshold=14)
