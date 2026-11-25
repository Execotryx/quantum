"""Build the pinned round12 recipe with explicitly named local kernel patches.

No notebook orchestration or verifier is run by this script. Source files stay
unchanged; each patch supplies install() and is hashed into the build report.
"""
from pathlib import Path
from contextlib import ExitStack
import argparse,hashlib,importlib.util,json,os,sys,time

ROOT=Path(os.environ.get('DQI_WORKSPACE','/workspace/scratch/0862b93a8b4f'))
SOURCE=ROOT/'recovered/round12/circuit_sources'
OFFICIAL=ROOT/'decoder/lab/official'
sys.dont_write_bytecode=True
sys.path[:0]=[str(SOURCE),str(OFFICIAL/'kickmix'),str(OFFICIAL/'dqi')]

def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--patch',type=Path,action='append',default=[])
 ap.add_argument('--output',type=Path,required=True)
 a=ap.parse_args();start=time.monotonic()
 recipe=json.loads((SOURCE/'selected_dqi.json').read_text());baseline_pin=recipe.pop('sha256')
 assert not recipe.pop('public_base',False)
 import round12_dqi,runtime,hankel_half,cyclic_gold
 from static_divisions import StaticDivisionDecoder
 original_record=StaticDivisionDecoder._record
 def record(b,name):
  original_record(b,name);row=b.stage_records[-1]
  row['elapsed_seconds']=time.monotonic()-start
  print(json.dumps(dict(event='stage',**row)),flush=True)
  a.output.with_suffix('.stages.json').write_text(json.dumps(b.stage_records,indent=2)+'\n')
 StaticDivisionDecoder._record=staticmethod(record)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 patch_records=[]
 with ExitStack() as stack:
  for i,path in enumerate(a.patch):
   path=path.resolve();sys.path.insert(0,str(path.parent))
   spec=importlib.util.spec_from_file_location(f'dqi_patch_{i}_{path.stem}',path)
   module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
   installed=module.install()
   if hasattr(installed,'__enter__'):stack.enter_context(installed)
   patch_records.append(dict(path=str(path),sha256=digest(path),installation_result=installed if isinstance(installed,(dict,list,str,int,float,bool)) else None))
  circuit,stages=round12_dqi.build_circuit(**recipe,competition=OFFICIAL)
  stats=circuit.operation_statistics()
  report=dict(scope='Full candidate build; verification is a separate step',baseline_sha256=baseline_pin,
   patches=patch_records,recipe=recipe,num_qubits=circuit.num_qubits,num_bits=circuit.num_bits,
   static_toffolis=stats.num_toffoli_like,num_ops=len(circuit),stages=stages,
   phase_arithmetic=getattr(circuit,'bezout_phase_arithmetic',None),build_seconds=time.monotonic()-start)
  a.output.with_suffix('.build.json').write_text(json.dumps(report,indent=2)+'\n')
  circuit.to_file(str(a.output),format='kmb')
  report.update(path=str(a.output.resolve()),sha256=digest(a.output),bytes=a.output.stat().st_size,
   elapsed_seconds=time.monotonic()-start)
  if not a.patch:assert report['sha256']==baseline_pin
  a.output.with_suffix('.build.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({k:v for k,v in report.items() if k not in ('recipe','stages')},indent=2),flush=True)

if __name__=='__main__':main()
