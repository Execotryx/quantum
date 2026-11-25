# SPDX-License-Identifier: Apache-2.0
"""Round13 leapfrog drop-in: unchanged public_v11 signatures."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parent
def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def setup(competition):
 competition=Path(competition)
 sys.path[:0]=[str(ROOT),str(competition/'kickmix'),str(competition/'verifiers'),str(competition/'verifiers/dqi')]
def build_invsqrt(out,work,competition):
 setup(competition)
 import kickmix as km
 import domain_compile as C
 from public_inv_payload import build
 recipe=json.loads((ROOT/'selected_inv78.json').read_text())
 work=Path(work)/'round13_inv78';work.mkdir(exist_ok=True,parents=True)
 base=build(work/'public_base');c=km.Circuit.from_file(str(base),format='kmb')
 raw=work/'raw.kmx';raw.write_text(str(c));del c
 candidate=work/'domain.kmx';C.compile(raw,candidate,max_x=3133452,linear=True)
 if recipe['stage']=='hmr':
  import round13_hmr as H
  target=work/'hmr.kmx';H.compile(candidate,target);candidate=target
 c=km.Circuit.from_file(str(candidate),format='kmx');out=Path(out);out.mkdir(exist_ok=True,parents=True)
 path=out/'invsqrt.kmb';c.to_file(str(path),format='kmb');assert digest(path)==recipe['sha256']
 return path
def build_dqi(out,work,competition):
 setup(competition)
 recipe=json.loads((ROOT/'selected_dqi.json').read_text());pin=recipe.pop('sha256')
 if recipe.pop('public_base',False):
  sys.path.insert(0,str(ROOT/'somejoint/runs/mad-dqi'))
  import runtime,hankel_half,cyclic_gold
  c,details=runtime.build_circuit(phase=hankel_half.forney,extraction=cyclic_gold.extract)
 else:
  from round12_dqi import build_circuit
  c,details=build_circuit(**recipe,competition=competition)
 out=Path(out);out.mkdir(exist_ok=True,parents=True);path=out/'dqi.kmb';c.to_file(str(path),format='kmb')
 assert digest(path)==pin
 return path
def build_dfthcsos(out,data_file):
 import chemistry_r5 as C
 return C.build_dfthcsos(out,data_file)
