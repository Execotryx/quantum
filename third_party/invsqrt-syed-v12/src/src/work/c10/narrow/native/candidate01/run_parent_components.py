#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Run small component jobs serially after checking the hard memory cap."""
from pathlib import Path
import hashlib,json,resource,subprocess,sys,time


def main():
    here=Path(__file__).resolve().parent;limit=512*1024**2
    assert resource.getrlimit(resource.RLIMIT_AS)==(limit,limit)
    try:bytearray(limit+1)
    except MemoryError:pass
    else:raise AssertionError('Hard address-space bound failed.')
    print(json.dumps(dict(guard_worker_preflight='PASS',hard_address_space=limit,oversize_allocation_rejected=True)),flush=True)
    results=[]
    jobs=[('prove_normalization.py',[]),('prove_root_decoder.py',[]),
          ('prove_divider.py',['--stage','all','--cases','8192','--seeds','0,1']),
          ('prove_tables.py',['--case','all']),('prove_lifecycle.py',[])]
    source_names=['common.py','normalization.py','root_decode.py','divider.py','tables.py',
                  'table_text_symbolic.py','lifecycle.py']+[name for name,_ in jobs]
    pins={name:hashlib.sha256((here/name).read_bytes()).hexdigest()for name in source_names}
    # A second queued launcher may wake after the same proof batch has already
    # run. It may reuse the exact hash-matched receipt, never repeat a failed
    # or unchanged workload automatically.
    claim=here/'component_batch_claim.json'
    try:
        with claim.open('x')as file:json.dump(dict(source_pins=pins,started_unix=time.time()),file,indent=2)
    except FileExistsError:
        receipt=here/'parent_components_receipt.json'
        if receipt.exists():
            old=json.loads(receipt.read_text())
            if old.get('status')=='PASS_NATIVE_ALL_COMPONENTS_NOT_OFFICIAL'and old.get('source_pins')==pins:
                print(json.dumps(dict(status='REUSED_HASH_MATCHED_COMPONENT_RECEIPT_NO_RERUN')),flush=True);return 0
        print(json.dumps(dict(status='PRIOR_COMPONENT_BATCH_INCOMPLETE_NO_AUTOMATIC_RETRY')),flush=True);return 4
    for script,arguments in jobs:
        started=time.monotonic();print(json.dumps(dict(component_start=script)),flush=True)
        result=subprocess.run([sys.executable,'-u',str(here/script),*arguments],check=False)
        results.append(dict(script=script,returncode=result.returncode,seconds=time.monotonic()-started))
        assert all(hashlib.sha256((here/name).read_bytes()).hexdigest()==digest for name,digest in pins.items()),'Component source changed during proof batch.'
        (here/'component_batch_partial.json').write_text(json.dumps(dict(status='PARTIAL',source_pins=pins,results=results),indent=2)+'\n')
        if result.returncode:return result.returncode
    (here/'parent_components_receipt.json').write_text(json.dumps(dict(status='PASS_NATIVE_ALL_COMPONENTS_NOT_OFFICIAL',source_pins=pins,results=results),indent=2)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
