# SPDX-License-Identifier: Apache-2.0
"""Own history/lifetime integration over SomeJoint's exact sub9 source.

SomeJoint/Agniv Banerjee: Hankel/Bezout and cyclic Gold phase/extraction;
ViberTeam/Artem Nazemtsev: paired kernels and norm recycling;
Phuc Thai: pair/gap-pointer ideas; Dmitrii Gluzdov: rank10 and mixed first pair.
"""
from pathlib import Path
from contextlib import contextmanager
import sys
L=Path(__file__).resolve().parent
S=L/'round12_source/somejoint/runs/mad-dqi'
if not S.exists():S=L/'somejoint/runs/mad-dqi'
sys.path.insert(0,str(S))

def build_circuit(history=10,threshold=14,mixed=False,lazy_tmp=False,replan=False,compact=False,stage_policy=None,own_reused=False,competition=None):
 if competition is not None:
  competition=Path(competition);sys.path[:0]=[str(competition/'kickmix'),str(competition/'verifiers'),str(competition/'verifiers/dqi')]
 import runtime,hankel_half,cyclic_gold
 if compact:
  from round11_dqi import install_inverses
  install_inverses()
 if own_reused:
  install_own_reused_scaling()
 if replan:
  from functools import cache
  import jfraction_decoder as J
  import model_fast_extraction as F
  original=J.power_plan
  @cache
  def planner(n,d):
   if n<=d:return 0,0
   return min((planner(m,d)[0]+42*F.toeplitz_plan(n-m,d)[0]+(cyclic_gold.plan(n,m)[0] if d==2 else 42*F.shear_cost(n,d,True,m)),m) for m in range((n+d-1)//d,n))
  J.power_plan=planner
 from common import build
 from jfraction_gap_decoder import GapJFractionDecoder
 from mask_projection import projected_record
 from merge_kernels import PointerBank,convert_pointers
 import matrix_pair_kernels as X
 X.BORROW_ZERO_META=True
 if lazy_tmp:
  import border_circuit as B,central_circuit as C,retry_circuit as R
  Original=B.Scaling
  class Lazy(Original):
   def __init__(self,b,pivot,counts):
    self.b,self.pivot,self.counts=b,pivot,counts
    self.zero=b.alloc_qubits(1)[0];b.flip_if_equal(pivot,0,target=self.zero);b.cx(self.zero,pivot[0])
    self.inverse=B.init_smallspace_inverse(b,pivot,field=B.GF);self.tmp=None;counts['inverse_groups']+=1
   def apply(self,word,divide):
    self.tmp=self.b.alloc_qubits(12);super().apply(word,divide);self.b.free(self.tmp);self.tmp=None
   def close(self):
    assert self.tmp is None
    b=self.b;B.clear_inverse_hmr(b,self.pivot,self.inverse,field=B.GF);b.free(self.inverse)
    b.cx(self.zero,self.pivot[0]);b.flip_if_equal(self.pivot,0,target=self.zero);b.free(self.zero)
  original_controlled=R.controlled_scale
  def controlled(scale,word,control,*,divide):
   scale.tmp=scale.b.alloc_qubits(12);original_controlled(scale,word,control,divide=divide);scale.b.free(scale.tmp);scale.tmp=None
  B.Scaling=C.Scaling=R.Scaling=Lazy;R.controlled_scale=C.controlled_scale=controlled
 class Decoder(GapJFractionDecoder):
  def build_syndrome_decoding_mbuc(self,b,*,syndromes,error_mbuc,n_iters):
   from round11_history import Rank10Stack
   from round11_dqi import history_view,stack_type
   words=list(syndromes);outcomes=projected_record(b,syndromes,error_mbuc);b.stage_records=[]
   bank=history_view(Rank10Stack(b)) if history==10 else stack_type()(b,35) if history==11 else PointerBank(b,35)
   def extract(reverse=False):
    with cyclic_gold.installed():
     if not mixed and stage_policy is None:return X.extract_hybrid(b,words,bank,reverse=reverse,fused=True,matrix_threshold=threshold)
     import merged_own as M
     from paired_kernels import single_step
     class Raw:
      def __getattr__(self,n):return getattr(bank,n)
      def push(self,index,flag):bank.core.push(index,flag)
      def pop(self,index,flag):bank.core.pop(index,flag)
     if stage_policy is not None:stages=[tuple(x) for x in stage_policy]
     else:
      stages=[(0,'own')];j=2
      while j<35:
       kind='matrix' if 70-2*j>=threshold else 'single';stages.append((j,kind));j+=2 if kind=='matrix' else 1
     for j,kind in reversed(stages) if reverse else stages:
      if kind=='own':M.pair(b,words[2*j:],Raw(),j,self.field,reverse=reverse)
      elif kind=='matrix':X.fused_matrix_pair_step(b,words[2*j:],bank,j,reverse=reverse)
      elif kind=='pair':
       from paired_kernels import pair_step
       pair_step(b,words[2*j:],bank,j,reverse=reverse)
      else:single_step(b,words[2*j:],bank,j,reverse=reverse)
   self._record(b,'initialization');extract();self._record(b,'moment_to_fraction')
   p,q=convert_pointers(b,words,bank,release_inverse='small');self._record(b,'fraction_to_polynomials')
   hankel_half.forney(b,p,q[1:],outcomes,field=self.field);self._record(b,'phase_correction')
   convert_pointers(b,words,bank,reverse=True,release_inverse='small');self._record(b,'polynomials_to_fraction')
   extract(True);bank.release_zero();self._record(b,'fraction_to_moments')
 b=runtime.make_builder();c=build(b,iterations=35,decoder_type=Decoder)
 return c,b.stage_records

def install_own_reused_scaling():
 """One-word specialization of the exact inherited reused-mask scaler."""
 import merged_own as M
 def scale_one(b,pivot,word,previous,field,*,divide):
  if previous is False:
   from jfraction_decoder import scale_words
   return scale_words(b,pivot,[word],divide=divide)
  from compact_lifetime_kernels import scale_active_reused_mask
  return scale_active_reused_mask(b,pivot,[word],previous,divide=divide)
 M.scale_one=scale_one
