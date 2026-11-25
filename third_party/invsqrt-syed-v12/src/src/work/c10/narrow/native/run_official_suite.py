#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Run the four original official salts after a complete native proof.

No domain, tolerance, seed, or shot override exists here. Only the original
verifier's documented batching option may differ. Every complete invocation
is recorded verbatim by its pinned wrapper.
Use one parent strict guard; this process starts children serially only.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,resource,subprocess,sys,time
HERE=Path(__file__).resolve().parent
WRAPPERS={
 256:(HERE/'candidate01/verify_official.py','bf7e23e34789c191c83e7ad03d5e28c690ba85da4c23d66705c16f544e020d63'),
 1792:(HERE/'verify_official_full1792.py','aef104e3b7f267b22401c4c8723685f4f1960b3072ec2f59dac5f3bb47172892'),
}
SALTS=('default','1','2','3');INPUTS=3133452;SHOTS=INPUTS*64


def atomic(path,data):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)


def check_proof(path,digest):
 proof=json.loads(path.read_text());assert proof['circuit_sha256']==digest
 assert proof['Q']<=52 and proof['input_interval']==[1,INPUTS+1] and proof['input_interval_end_exclusive']
 assert proof['proved_inputs']==INPUTS and proof['whole_official_domain']
 for name in ['every_HMR_transcript_proved','original_input_register_restored','scratch_zero','all_resets_provably_zero','phase_exactly_matches_frozen_integer_model','unchanged_original_tolerance']:
  assert proof[name],name
 modulus=proof.get('phase_modulus',1<<37)
 assert modulus in (1<<37,1<<50),'An explicit reviewed integer phase model is required.'
 if modulus==1<<50:
  assert proof['phase_exactly_matches_quantized_integer50_model']
  assert proof['independent_full_quantize50_digest_matched']
  assert proof['all_phase_checks_enabled'] and len(proof['phase_units50_sha256'])==64
 stop=1
 for row in proof['chunks']:
  assert row['first']==stop and row['stop']-row['first']==row['inputs']
  assert row['status']=='PROVED_EXACT_NATIVE_TEXT_ALL_HMR_TRANSCRIPTS'
  assert row['every_HMR_transcript_proved'] and row['original_x_restored'] and row['all_scratch_zero']
  assert row['final_HMR_phase_terms']==0 and row['all_fractional_phase_predicates_HMR_independent']
  assert row['modulus']==modulus and row['phase_denominator']==modulus//2
  stop=row['stop']
 assert stop==INPUTS+1
 return proof


def main():
 ap=argparse.ArgumentParser();ap.add_argument('circuit',type=Path);ap.add_argument('--native-proof',type=Path,required=True)
 ap.add_argument('--output-dir',type=Path,required=True);ap.add_argument('--max-workers',type=int,default=2)
 ap.add_argument('--max-new-salts',type=int,choices=(1,2,3,4),default=2,
  help='Bound this serial group; resume from exact same-circuit PASS records. Qualification still requires all four salts.')
 ap.add_argument('--batch-size',type=int,choices=(256,1792),default=1792,
  help='Documented original verifier batching; every original input and64 shots remain mandatory.')
 args=ap.parse_args()
 assert resource.getrlimit(resource.RLIMIT_AS)[1]==640*1024**2,'Parent official-only split guard required'
 assert args.max_workers==2,'Official workload is split into exactly two workers'
 wrapper,wrapper_sha=WRAPPERS[args.batch_size]
 assert SHOTS%args.batch_size==0
 assert hashlib.sha256(wrapper.read_bytes()).hexdigest()==wrapper_sha
 circuit=args.circuit.resolve();digest=hashlib.sha256(circuit.read_bytes()).hexdigest()
 proof=check_proof(args.native_proof,digest);out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
 began=time.monotonic();results=[];new_salts=0
 summary=dict(status='OFFICIAL_SUITE_RUNNING_NOT_QUALIFIED',circuit_sha256=digest,
  native_proof_sha256=hashlib.sha256(args.native_proof.read_bytes()).hexdigest(),Q=proof['Q'],
  required_salts=list(SALTS),required_inputs=INPUTS,shots_per_input=64,
  original_tolerance_unchanged=True,verifier_wrapper_sha256=wrapper_sha,no_submission=True,
  batch_size=args.batch_size,max_workers=args.max_workers,full_original_verifier_checks=True,
  started_utc=datetime.now(timezone.utc).isoformat(),max_new_salts_this_group=args.max_new_salts,
  qualified=False,results=results)
 atomic(out/'qualification.partial.json',summary)
 for salt in SALTS:
  record=out/(salt+'.record.json')
  if record.exists():
   stored=json.loads(record.read_text())
   assert stored['status']=='PASS' and stored['circuit_sha256']==digest and stored['salt']==salt,'Existing evidence must be a completed PASS of this exact circuit and salt'
   assert stored.get('batch_size',256)==args.batch_size,'Keep each suite at its recorded batch size.'
  else:
   if new_salts==args.max_new_salts:
    break
   new_salts+=1
   cmd=[sys.executable,'-u',str(wrapper),str(circuit),'--salt',salt,'--output-dir',str(out),'--max-workers',str(args.max_workers)]
   print(json.dumps(dict(starting_original_official_salt=salt,circuit_sha256=digest)),flush=True)
   child=subprocess.run(cmd,check=False,timeout=1800)
   if child.returncode:
    summary.update(status='OFFICIAL_SUITE_STOPPED_NOT_QUALIFIED',failed_salt=salt,exit_code=child.returncode,elapsed_seconds=time.monotonic()-began)
    atomic(out/'qualification.partial.json',summary);raise SystemExit(child.returncode)
   stored=json.loads(record.read_text())
  official=stored['official_result']
  assert stored['status']=='PASS' and official['status']=='PASS'
  assert stored['circuit_sha256']==digest and official['circuit_sha256']==digest
  assert official['verified_shots']==SHOTS and official['num_qubits']==proof['Q']
  results.append(dict(salt=salt,official_result=official,record_sha256=hashlib.sha256(record.read_bytes()).hexdigest(),official_json_sha256=hashlib.sha256((out/(salt+'.json')).read_bytes()).hexdigest()))
  summary.update(results=results,elapsed_seconds=time.monotonic()-began)
  atomic(out/'qualification.partial.json',summary)
 if len(results)!=len(SALTS):
  summary.update(status='OFFICIAL_SUITE_GROUP_COMPLETE_NOT_YET_QUALIFIED',qualified=False,
   new_salts_completed_this_group=new_salts,pending_salts=list(SALTS[len(results):]),
   elapsed_seconds=time.monotonic()-began,finished_group_utc=datetime.now(timezone.utc).isoformat())
  atomic(out/'qualification.partial.json',summary);print(json.dumps(summary,indent=2),flush=True)
  return
 assert tuple(r['salt']for r in results)==SALTS
 scores=[r['official_result']['score']for r in results];worst=max(scores)
 summary.update(status='QUALIFIED_FOUR_ORIGINAL_SALTS_AND_COMPLETE_NATIVE_PROOF',qualified=True,
  default_score=scores[0],score_range=[min(scores),worst],conservative_score=worst,
  total_official_shots=4*SHOTS,all_salts_beat_stage97=worst<92278.95,all_salts_meet_target=worst<=89987,
  all_salts_meet_stretch=worst<=82740,finished_utc=datetime.now(timezone.utc).isoformat())
 atomic(out/'qualification.json',summary);print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
