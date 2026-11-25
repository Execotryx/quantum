# SPDX-License-Identifier: Apache-2.0
"""Source reimplementation of phucthaiv02 EXP118c buffer and lean scan ideas.

Underlying J-fraction: SomeJoint/Agniv Banerjee. Mask projection: manwithacat.
No public binary inputs. This deliberately retains all 35 exact gap flags.
"""
import os,sys,json,time,hashlib,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def install(competition=None):
 import qcc_pipeline as P
 assert competition is not None, 'competition_dir is required'
 P.setup(competition)
 import jfraction_gap_decoder as G
 if getattr(G,'_round6_buffer_installed',False):return G
 import inspect
 source=inspect.getsource(G.scale_active)
 # HMR has reset temporary; all subsequent repairs depend on word/factor/mask.
 source=source.replace('builder.hmr(temporary, mask)','builder.hmr(temporary, mask)\n    builder.free(temporary)')
 source=source.replace('    builder.free(temporary)\n    builder.del_gf2_inverse','    builder.del_gf2_inverse')
 exec(compile(source,'<round6-free-extraction-buffer>','exec'),G.__dict__)
 G._round6_buffer_installed=True
 return G

def lean_forney(b,numerator,denominator,outcomes,field):
 """Natural polynomial scan, implicit constant 1; retained 10-wire zero chain."""
 import kickmix as km
 sigma=denominator[2];deriv=denominator[1];omega=numerator[0]
 inv=b.alloc_qubits(12);flag=b.alloc_qubits(1)[0];chain=b.alloc_qubits(10)
 active=b.alloc_bits(1)
 terms=[(word,field.pow(field.primitive_element,-k %4095)) for k,word in enumerate(denominator[1:],1)]
 terms += [(word,field.pow(field.primitive_element,-k %4095)) for k,word in enumerate(numerator) if k]
 for j,mask in enumerate(outcomes):
  b.bit_store(active[0],True,control=mask);b.push_condition(active[0])
  b.x(sigma[0])
  for k in range(3,len(denominator),2):b.cx(denominator[k],deriv)
  for k in range(4,len(denominator),2):b.cx(denominator[k],sigma)
  b.cx(deriv,sigma)
  for word in numerator[1:]:b.cx(word,omega)
  b.x(sigma)
  b.init_and(sigma[0],sigma[1],chain[0])
  for k in range(1,10):b.init_and(chain[k-1],sigma[k+1],chain[k])
  b.init_and(chain[-1],sigma[-1],flag);b.x(sigma)
  _,scaffold=b.init_controlled_inverse(deriv,flag,target=inv)
  scale=field.pow(field.primitive_element,-j%4095)
  b.gf2_imul(scale,target=omega,field=field)
  b.gf2_phase_by_product(omega,inv,mask=mask,field=field)
  b.gf2_idiv(scale,target=omega,field=field)
  b.del_controlled_inverse(deriv,flag,target=inv,scaffold=scaffold);b.free(scaffold)
  b.x(sigma);b.del_and(chain[-1],sigma[-1],flag)
  for k in reversed(range(1,10)):b.del_and(chain[k-1],sigma[k+1],chain[k])
  b.del_and(sigma[0],sigma[1],chain[0]);b.x(sigma)
  for word in reversed(numerator[1:]):b.cx(word,omega)
  b.cx(deriv,sigma)
  for k in reversed(range(4,len(denominator),2)):b.cx(denominator[k],sigma)
  for k in reversed(range(3,len(denominator),2)):b.cx(denominator[k],deriv)
  b.x(sigma[0]);b.pop_condition();b.bit_store(active,False)
  if j<4094:
   for word,step in terms:b.gf2_imul(step,target=word,field=field)
 for word,step in terms:b.gf2_idiv(field.pow(step,4094),target=word,field=field)
 b.free(active);b.free(inv+chain+km.array([flag]))

def build_dqi(out,work=None,*,lean=True,competition=None):
 G=install(competition)
 # The mask wrapper's loader may insert its own source path; imports already
 # pin the SomeJoint modules from round4_source above.
 import port_pipeline as PP
 M=PP.module('ports6_mask',ROOT/'dqi/continued_fraction/mask_projection.py')
 class Decoder(G.GapJFractionDecoder):
  def build_syndrome_decoding_mbuc(self,builder,*,syndromes,error_mbuc,n_iters):
   b=builder;words=list(syndromes);b.stage_records=[]
   outcomes=M.projected_record(b,syndromes,error_mbuc)
   flags=b.alloc_qubits(35);self._record(b,'initialization')
   G.extract_gap(b,words,flags);self._record(b,'moment_to_fraction')
   numerator,denominator=G.convert_gap(b,words,flags);self._record(b,'fraction_to_polynomials')
   if lean:lean_forney(b,numerator,denominator,outcomes,self.field)
   else:
    one=b.alloc_qubits(12);b.x(one[0]);denominator[0]=one
    G.CompactEuclidDecoder(70,self.field)._forney(b,numerator,denominator,True,outcomes)
    b.x(one[0]);b.free(one)
   self._record(b,'phase_correction');G.convert_gap(b,words,flags,reverse=True)
   self._record(b,'polynomials_to_fraction');G.extract_gap(b,words,flags,reverse=True)
   b.free(flags);self._record(b,'fraction_to_moments')
 b=G.StaticArithmeticBuilder();c=G.build(b,iterations=35,decoder_type=Decoder)
 out=Path(out);out.mkdir(parents=True,exist_ok=True);p=out/'dqi.kmb';c.to_file(str(p),format='kmb')
 (out/'build.json').write_text(json.dumps(dict(num_qubits=c.num_qubits,num_bits=c.num_bits,stages=b.stage_records),indent=2))
 return p
