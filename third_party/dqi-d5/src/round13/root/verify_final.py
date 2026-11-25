"""Run the unchanged official verifier only for the selected final candidate."""
from pathlib import Path
import argparse,hashlib,json,os,sys,time
ROOT=Path(os.environ.get('DQI_WORKSPACE','/workspace/scratch/0862b93a8b4f'))
OFFICIAL=ROOT/'decoder/lab/official'
sys.dont_write_bytecode=True
sys.path[:0]=[str(OFFICIAL/'kickmix'),str(OFFICIAL/'dqi')]
import kickmix as km
import verify_submission_dqi as verify

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('circuit',type=Path)
 ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--num-shots',type=int,default=102400)
 ap.add_argument('--salt',default='quant-fixed-development-v1')
 a=ap.parse_args();start=time.monotonic()
 with Path(verify.__file__).open('rb') as f:verifier_sha=hashlib.file_digest(f,'sha256').hexdigest()
 assert verifier_sha=='f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65'
 circuit=km.Circuit.from_file(str(a.circuit),format='kmb')
 report=verify.verify(circuit,verify.ProblemSpecDQI.benchmark_instance(num_shots=a.num_shots),
   salt=a.salt,seed=None,max_workers=1)
 report.update(elapsed_seconds=time.monotonic()-start,official_verifier_sha256=verifier_sha,
   development_salt=a.salt,seed_override=None,reference_cost=24439473914136.668,
   reference_ratio=24439473914136.668/report['score'])
 a.output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
