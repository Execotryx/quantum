"""Run unchanged official DQI verification with passive progress checkpoints.

The trace hook only observes Python locals/return values. It does not replace
verification functions, change inputs, supply a seed override, or edit locals.
The official verify() return is still required for the final PASS report.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,os,sys,time
ROOT=Path(os.environ.get('DQI_WORKSPACE','/workspace/scratch/0862b93a8b4f'))
OFFICIAL=ROOT/'decoder/lab/official'
sys.dont_write_bytecode=True
sys.path[:0]=[str(OFFICIAL/'kickmix'),str(OFFICIAL/'dqi')]
import numpy as np
import kickmix as km
import verify_submission_dqi as verify
PIN='f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('circuit',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--num-shots',type=int,default=102400)
    p.add_argument('--salt',default='quant-fixed-development-v1')
    p.add_argument('--max-workers',type=int,default=4)
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);started=time.monotonic()
    code_path=Path(verify.__file__);sha=hashlib.sha256(code_path.read_bytes()).hexdigest();assert sha==PIN
    code=code_path.read_text().splitlines()
    depth_line=next(i+1 for i,line in enumerate(code)if "'reaction_depth': circuit.reaction_depth()"in line)
    c=km.Circuit.from_file(str(a.circuit),format='kmb')
    spec=verify.ProblemSpecDQI.benchmark_instance(num_shots=a.num_shots)
    batch_path=a.output.with_suffix('.batches.jsonl')
    if batch_path.exists():raise FileExistsError(f'Refusing to overwrite existing run checkpoints: {batch_path}')
    # An append-only descriptor remains safe across the verifier's worker forks.
    fd=os.open(batch_path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    parent_pid=os.getpid();depth_saved=False
    def trace(frame,event,arg):
        nonlocal depth_saved
        if frame.f_code.co_filename!=verify.__file__:return None
        name=frame.f_code.co_name
        if name not in ('verify','run_batch'):return None
        if name=='run_batch'and event=='return'and arg is not None:
            f=frame.f_locals
            row={'start':int(f['start']),'stop':int(f['stop']),'rng_seed':int(f['rng_seed']),'sim_seed':int(f['sim_seed']),
                 'value_errors':int(arg[0]),'phase_errors':int(arg[1]),'toffoli_sum':int(arg[2]),'operation_counts':arg[3]}
            os.write(fd,(json.dumps(row,separators=(',',':'))+'\n').encode())
        if name=='verify'and event=='line'and frame.f_lineno==depth_line and not depth_saved:
            f=frame.f_locals;depth_saved=True
            report={'status':'VERIFICATION_CHECKS_PASSED_REPORT_PENDING',
                    'verified_shots':int(f['num_shots']),'value_errors':int(f['value_errors']),'phase_errors':int(f['phase_errors']),
                    'empirical_error_rate':float(f['eps_hat']),'effective_error_rate':float(f['eps_plus']),
                    'log2_delta':float(f['log2_delta']),'repetition_factor':float(f['rep_factor']),
                    'toffoli_count':float(f['toffolis']),'num_qubits':int(f['num_qubits']),
                    'score_before_depth_metadata':float(f['rep_factor']*f['num_qubits']**2*f['toffolis']),
                    'circuit_sha256':f['circuit_hash'],'official_verifier_sha256':sha,
                    'development_salt':a.salt,'seed_override':None,'max_workers':a.max_workers,
                    'elapsed_seconds':time.monotonic()-started,
                    'note':'Observed unchanged verifier locals immediately before native reaction_depth(); final official return still pending.'}
            a.output.with_suffix('.before_depth.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({'event':'verification_checks_completed','value_errors':report['value_errors'],
                              'phase_errors':report['phase_errors'],'shots':report['verified_shots']}),flush=True)
        return trace
    print(json.dumps({'event':'starting_official_verification','shots':a.num_shots,'max_workers':a.max_workers,
                      'verifier_sha256':sha,'passive_checkpoints':str(batch_path)}),flush=True)
    sys.settrace(trace)
    try:
        report=verify.verify(c,spec,salt=a.salt,seed=None,max_workers=a.max_workers)
    finally:
        sys.settrace(None);os.close(fd)
    report.update(elapsed_seconds=time.monotonic()-started,official_verifier_sha256=sha,
                  development_salt=a.salt,seed_override=None,max_workers=a.max_workers,
                  reference_cost=24439473914136.668,reference_ratio=24439473914136.668/report['score'],
                  passive_trace='Only records batch return values and pre-depth locals; official functions and locals unchanged.')
    rows=[json.loads(s)for s in batch_path.read_text().splitlines()]
    assert len(rows)==a.num_shots//256 and len({r['start']for r in rows})==len(rows)
    assert sum(r['value_errors']for r in rows)==report['value_errors']
    assert sum(r['phase_errors']for r in rows)==report['phase_errors']
    assert sum(r['toffoli_sum']for r in rows)/a.num_shots==report['toffoli_count']
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
