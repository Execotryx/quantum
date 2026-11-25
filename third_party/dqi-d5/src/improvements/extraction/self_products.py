"""Specialize extraction self-products and reuse the HMR-cleared top word.

The polynomial bank map and shortened-series extension remain exact.
"""
from functools import cache
from gold17 import xor_gold17

_ORIGINAL=None

def same(a,b):return not isinstance(a,int)and not isinstance(b,int)and tuple(a)==tuple(b)

def term_cost(a,b,lf,rf):
 if isinstance(a,int)or isinstance(b,int):return 0
 if same(a,b):
  if lf==rf:return 0
  if (lf,rf)in ((2,1),(1,2)):return 26
  if (lf,rf)in ((16,1),(1,16)):return 27
 return 42

def term(b,a,c,target,lf=1,rf=1):
 from poly_arithmetic import GF,add_scaled
 from gold_forms import transform_word
 import gold_cube
 if isinstance(a,int):add_scaled(b,c,target,GF.pow(a,lf),rf);return
 if isinstance(c,int):add_scaled(b,a,target,GF.pow(c,rf),lf);return
 if same(a,c):
  if lf==rf:add_scaled(b,a,target,frobenius=2*lf);return
  if(lf,rf)in((2,1),(1,2)):gold_cube.xor_cube(b.native,a,target);return
  if(lf,rf)in((16,1),(1,16)):xor_gold17(b,a,target);return
  temp=b.alloc_qubits(12);add_scaled(b,a,temp,frobenius=rf)
  transform_word(b,a,frobenius=lf)
  b.ixor_gf2_mul(a,temp,target=target,field=GF)
  transform_word(b,a,frobenius=lf,inverse=True)
  add_scaled(b,a,temp,frobenius=rf);b.free(temp);return
 transform_word(b,a,frobenius=lf);transform_word(b,c,frobenius=rf)
 b.ixor_gf2_mul(a,c,target=target,field=GF)
 transform_word(b,c,frobenius=rf,inverse=True);transform_word(b,a,frobenius=lf,inverse=True)

def accumulate(b,lhs,rhs,targets,*,left_frobenius=1,right_frobenius=1,method='auto'):
 size=len(lhs)+len(rhs)-1
 assert len(targets)==size
 active=[i for i,w in enumerate(targets)if w is not None]
 if not active:return 0
 terms=[(i,j)for i in range(len(lhs))for j in range(len(rhs))if targets[i+j]is not None]
 naive=sum(term_cost(lhs[i],rhs[j],left_frobenius,right_frobenius)for i,j in terms)
 rank=min(size,min(len(lhs),len(rhs))+active[-1]-active[0])
 if method not in('auto','schoolbook')or(method=='auto'and naive>42*rank):
  return _ORIGINAL(b,lhs,rhs,targets,left_frobenius=left_frobenius,right_frobenius=right_frobenius,method=method)
 input_ids={q for w in[*lhs,*rhs]if not isinstance(w,int)for q in w};target_ids=[q for w in targets if w is not None for q in w]
 assert not input_ids.intersection(target_ids)and len(target_ids)==len(set(target_ids))
 for i,j in terms:term(b,lhs[i],rhs[j],targets[i+j],left_frobenius,right_frobenius)
 return len(terms)

def top_power_update(b,words,d,shortened):
 from poly_arithmetic import GF,add_scaled
 last=len(words)-1;terms=[(i,last-d*i)for i in range(1,last//d+1)]
 if not terms:return
 assert all(j>0 for _,j in terms)
 delta=b.alloc_qubits(12)
 for i,j in terms:term(b,words[i],words[j],delta,d,1)
 b.x(shortened);b.gf2_iadd(delta,target=words[-1],control=shortened,field=GF);b.x(shortened)
 mask=b.alloc_bits(12);b.hmr(delta,mask)
 # The measured delta is zero and can hold each Frobenius form for correction.
 for i,j in terms:
  add_scaled(b,words[i],delta,frobenius=d)
  b.gf2_phase_by_product(delta,words[j],mask=mask,field=GF)
  add_scaled(b,words[i],delta,frobenius=d)
 b.free(mask+delta)

def install():
 global _ORIGINAL
 import jfraction_decoder as J,jfraction_gap_decoder as G
 if _ORIGINAL is None:_ORIGINAL=J.accumulate_product
 J.accumulate_product=accumulate;G.top_power_update=top_power_update
