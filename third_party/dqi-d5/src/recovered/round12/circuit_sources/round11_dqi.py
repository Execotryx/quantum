# SPDX-License-Identifier: Apache-2.0
"""Round11 source integration: own merged and borrowed-stack hybrid variants.

Credits: Artem Nazemtsev (norm recycling, matrix pair source); Phuc Thai
(pairing); SomeJoint (J-fraction); Dmitrii Gluzdov (own merged/stack path).
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import argparse,gc,json,sys,time
ROOT=Path(__file__).resolve().parent;SRC=ROOT if (ROOT/'merged_own.py').exists() else ROOT/'round11_source/own'
COMP=Path(os.environ.get('QCC_COMP','.'))

def setup(competition=None):
 comp=Path(competition) if competition is not None else COMP
 sys.path[:0]=[str(SRC),str(SRC/'dqi'),str(SRC/'dqi/continued_fraction'),str(comp/'kickmix'),str(comp/'verifiers'),str(comp/'verifiers/dqi')]

def install_inverses():
 import round9_pointer as P,compact_lifetime_kernels as K,jfraction_decoder as J
 from norm_recycle_inverse import init_norm_recycle_inverse
 from smallspace_inverse import clear_inverse_hmr
 P.install_compact_scaling()
 def unwrap(b):
  while hasattr(b,'builder'):b=b.builder
  return b
 def initialize(b,source,*,field):return init_norm_recycle_inverse(unwrap(b),source,field=field)
 def delete(b,source,target,*,field):clear_inverse_hmr(unwrap(b),source,target,field=field)
 K.init_compact_inverse=J.init_compact_inverse=initialize
 K.delete_compact_inverse=J.delete_compact_inverse=delete
 import smallspace_inverse as S
 S.init_smallspace_inverse=init_norm_recycle_inverse


def stack_type():
 from round9_pointer import GapStack
 class Stack(GapStack):
  def __init__(self,b,count):super().__init__(b,older_width=5);self.count=count
  def xor_read(self,index,target):self.equal(self.a,index,target);self.equal(self.old,index,target)
  def read(self,index):
   q=self.b.alloc_qubits(1)[0];self.xor_read(index,q);return q
  def unread(self,index,target):self.xor_read(index,target);self.b.free(target)
  def push(self,index,flag):super().push(index,flag);self.b.free(flag)
  def pop(self,index):
   flag=self.b.alloc_qubits(1)[0];super().pop(index,flag);return flag
  def release_zero(self):self.release()
 return Stack


def history_view(core):
 class View:
  def __init__(self):self.b=core.b;self.core=core;self.count=35
  def __getattr__(self,name):return getattr(core,name)
  def xor_read(self,index,target):core.xor_read(index,target)
  def read(self,index):
   q=self.b.alloc_qubits(1)[0];self.xor_read(index,q);return q
  def unread(self,index,target):self.xor_read(index,target);self.b.free(target)
  def push(self,index,flag):core.push(index,flag);self.b.free(flag)
  def pop(self,index):
   q=self.b.alloc_qubits(1)[0];core.pop(index,q);return q
  def release_zero(self):core.release()
 return View()


def build_circuit(mode='merged',threshold=14,forney='lean',leaf='mc4',competition=None,history=11):
 setup(competition);install_inverses()
 import merged_own as M,round6_dqi as R,round9_pointer as P
 from common import build
 from jfraction_gap_decoder import GapJFractionDecoder
 from mask_projection import projected_record
 from mc4_inverse import builder_class
 from phase_tensor import forney_tensor
 if leaf=='combined':
  import round10_dqi as L
  Builder=L.builder_type(combined=True)
 else:Builder=builder_class()
 class Decoder(GapJFractionDecoder):
  def build_syndrome_decoding_mbuc(self,builder,*,syndromes,error_mbuc,n_iters):
   b=builder;b.stage_records=[];words=list(syndromes);outcomes=projected_record(b,syndromes,error_mbuc)
   if mode=='merged':
    if history==10:
     from round11_history import Rank10Stack
     stack=Rank10Stack(b)
    else:stack=P.GapStack(b,older_width=5)
    extract=lambda reverse=False:M.extract(b,words,stack,self.field,reverse=reverse)
    if history==10:
     from merge_kernels import convert_pointers
     view=history_view(stack)
     convert=lambda reverse=False:convert_pointers(b,words,view,reverse=reverse,release_inverse='small')
    else:convert=lambda reverse=False:P.convert_short_lifetime(b,words,stack,reverse=reverse)
    release=stack.release
   else:
    import matrix_pair_kernels as X
    from merge_kernels import PointerBank,convert_pointers
    X.BORROW_ZERO_META=True
    if history==10:
     from round11_history import Rank10Stack
     stack=history_view(Rank10Stack(b))
    else:stack=stack_type()(b,35) if mode in ('hybrid-stack','mixed') else PointerBank(b,35)
    extract=lambda reverse=False:X.extract_hybrid(b,words,stack,reverse=reverse,matrix_threshold=threshold,fused=True)
    if mode=='mixed':
     class RawStack:
      def __getattr__(self,name):return getattr(stack,name)
      def push(self,index,flag):
       if history==10:stack.core.push(index,flag)
       else:P.GapStack.push(stack,index,flag)
      def pop(self,index,flag):
       if history==10:stack.core.pop(index,flag)
       else:P.GapStack.pop(stack,index,flag)
     def mixed_extract(reverse=False):
      from paired_kernels import single_step
      stages=[(0,'own')];j=2
      while j<35:
       kind='matrix' if 70-2*j>=threshold else 'single';stages.append((j,kind));j+=2 if kind=='matrix' else 1
      for j,kind in reversed(stages) if reverse else stages:
       if kind=='own':M.pair(b,words,RawStack(),0,self.field,reverse=reverse)
       elif kind=='matrix':X.fused_matrix_pair_step(b,words[2*j:],stack,j,reverse=reverse)
       else:single_step(b,words[2*j:],stack,j,reverse=reverse)
     extract=mixed_extract

    convert=lambda reverse=False:convert_pointers(b,words,stack,reverse=reverse,release_inverse='small')
    release=stack.release_zero
   self._record(b,'initialization');extract();self._record(b,'moment_to_fraction')
   numerator,denominator=convert();self._record(b,'fraction_to_polynomials')
   if forney=='tensor':forney_tensor(b,numerator,denominator[1:],outcomes,field=self.field)
   else:R.lean_forney(b,numerator,denominator,outcomes,self.field)
   self._record(b,'phase_correction');convert(True);self._record(b,'polynomials_to_fraction')
   extract(True);release();self._record(b,'fraction_to_moments')
 b=Builder();b.compact_first_division=True;c=build(b,iterations=35,decoder_type=Decoder)
 return c,dict(mode=mode,threshold=threshold,forney=forney,leaf=leaf,stages=b.stage_records)

def main():
 import round11_verify as D
 ap=argparse.ArgumentParser();ap.add_argument('--mode',nargs='+',default=['merged','hybrid-stack']);ap.add_argument('--threshold',type=int,default=14);ap.add_argument('--forney',default='lean');ap.add_argument('--leaf',default='mc4');ap.add_argument('--history',type=int,default=11);ap.add_argument('--verify',action='store_true');a=ap.parse_args()
 setup();D.start_audit();rows=[]
 for mode in a.mode:
  name=f'DQI-{mode.upper()}-{a.forney.upper()}-{a.leaf.upper()}-M{a.threshold}'+(f'-H{a.history}' if a.history!=11 else '');folder=D.OUT/name;folder.mkdir(exist_ok=True)
  D.progress('build',candidate=name);start=time.monotonic();c,row=build_circuit(mode,a.threshold,a.forney,a.leaf,history=a.history)
  stats=c.operation_statistics();row.update(name=name,num_qubits=c.num_qubits,num_bits=c.num_bits,static_toffoli=stats.num_toffoli_like,build_seconds=time.monotonic()-start)
  path=folder/'dqi.kmb';c.to_file(str(path),format='kmb');row.update(sha256=D.sha(path),path=str(path.relative_to(D.OUT)));D.record(name+'_build.json',row);D.progress('built',**{k:v for k,v in row.items() if k!='stages'})
  del c;gc.collect()
  if a.verify:row['official']=D.measure('dqi',path,name)
  rows.append(row);D.record('dqi_results.json',rows)
 D.finish_audit();D.progress('done')
if __name__=='__main__':main()
