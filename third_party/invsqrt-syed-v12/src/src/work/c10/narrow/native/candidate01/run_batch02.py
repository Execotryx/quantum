#!/usr/bin/env python3
# Copyright2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Resume after the corrected permanent-register fixture issue.

Successful normalization evidence is reused. The independent bias paper
screen is first, then the remaining native components, integration emission,
sampled diagnostics and a bounded all-outcome native-text diagnostic.
"""
from pathlib import Path
import hashlib,json,resource,subprocess,sys,time


def main():
    here=Path(__file__).resolve().parent;narrow=here.parents[1]
    assert resource.getrlimit(resource.RLIMIT_AS)==(512*1024**2,512*1024**2)
    norm=json.loads((here/'normalization_native_proof.json').read_text())
    assert norm['status']=='PASS_NATIVE_COMPONENT_NOT_OFFICIAL'
    assert hashlib.sha256((here/'normalization_roundtrip.kmb').read_bytes()).hexdigest()==norm['roundtrip_kmb_sha256']
    jobs=[(narrow/'research/postgate_phase_bias/screen.py',[]),
          (here/'prove_root_decoder.py',[]),
          (here/'prove_divider.py',['--stage','all','--cases','8192','--seeds','0,1']),
          (here/'prove_tables.py',['--case','all']),
          (here/'prove_lifecycle.py',[]),
          (here/'generate.py',[]),
          (here/'prove_whole.py',['--mode','sample','--shots','8192','--seeds','0,1,2,3','--output',str(here/'whole_native_sample.json')]),
          (here/'prove_whole.py',['--mode','text','--first','1','--last','1025','--chunk','1024','--output',str(here/'whole_text_first1024.json')])]
    files=list(here.glob('*.py'))+[narrow/'research/postgate_phase_bias/screen.py']
    pins={str(p.relative_to(narrow)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
    results=[];started=time.monotonic()
    for path,arguments in jobs:
        before=time.monotonic();print(json.dumps(dict(job_start=str(path.relative_to(narrow)),arguments=arguments)),flush=True)
        r=subprocess.run([sys.executable,'-u',str(path),*arguments],check=False)
        results.append(dict(job=str(path.relative_to(narrow)),arguments=arguments,returncode=r.returncode,seconds=time.monotonic()-before))
        assert all(hashlib.sha256((narrow/name).read_bytes()).hexdigest()==pin for name,pin in pins.items()),'Source changed during guarded batch.'
        report=dict(status='PARTIAL'if r.returncode==0 else'FAILED_JOB_STOPPED_NO_RETRY',source_pins=pins,results=results,
                    reused_normalization_proof_sha256=hashlib.sha256((here/'normalization_native_proof.json').read_bytes()).hexdigest(),seconds=time.monotonic()-started)
        (here/'batch02_partial.json').write_text(json.dumps(report,indent=2)+'\n')
        if r.returncode:return r.returncode
    report['status']='PASS_COMPONENTS_AND_COMPLETE_NATIVE_DIAGNOSTICS_NOT_OFFICIAL'
    (here/'batch02_receipt.json').write_text(json.dumps(report,indent=2)+'\n');return 0


if __name__=='__main__':raise SystemExit(main())
