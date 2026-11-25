"""Build the reviewed base or a registered structural variant; never verify silently."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import runtime

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('output',type=Path)
    ap.add_argument('--phase-module',type=Path)
    ap.add_argument('--extraction-module',type=Path)
    ap.add_argument('--base',action='store_true')
    args=ap.parse_args()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    target=out/'dqi.kmb'
    assert not target.exists(),target
    started=time.monotonic()
    phase=None
    extraction=None
    if args.phase_module:
        spec=importlib.util.spec_from_file_location('candidate_phase',args.phase_module.resolve())
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        phase=module.forney
    if args.extraction_module:
        spec=importlib.util.spec_from_file_location('candidate_extraction',args.extraction_module.resolve())
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        extraction=module.extract
    print('BUILD START',datetime.datetime.now(datetime.timezone.utc).isoformat(),flush=True)
    c,stages=runtime.build_circuit(phase=phase,extraction=extraction)
    c.to_file(str(target),format='kmb')
    with target.open('rb') as f:
        digest=hashlib.file_digest(f,'sha256').hexdigest()
    st=c.operation_statistics()
    record=dict(status='BUILT_NOT_VERIFIED',num_qubits=c.num_qubits,
        static_toffolis=st.num_toffoli_like,t_count=st.num_t_like,num_ops=len(c),
        num_bits=c.num_bits,sha256=digest,bytes=target.stat().st_size,
        build_seconds=time.monotonic()-started,stages=stages,
        base=args.base,phase_module=str(args.phase_module) if args.phase_module else None,
        extraction_module=str(args.extraction_module) if args.extraction_module else None,
        hostname=platform.node(),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
        sources={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in HERE.rglob('*.py')})
    (out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2),flush=True)
    if args.base:
        assert digest=='1161f7221de935ba1399ced409b9936d8b4cb570ef3314585d4b9bc2c5b24dd9',digest

if __name__=='__main__':main()
