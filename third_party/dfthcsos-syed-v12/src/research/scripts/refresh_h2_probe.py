#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Bounded H2-only probe after the newly measured one-body refresh.

Words and two-body weights are frozen. This reuses the team's HRepair routine;
it does not qualify a circuit package. Exact model and official physical checks
are reported separately, and only a feasible no-worse-lambda candidate is kept.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from fastchem import Ref,Model,decode,official
from pipeline import show
from repair import HRepair


def main():
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path)
    ap.add_argument('output',type=Path);ap.add_argument('--maxiter',type=int,default=240)
    args=ap.parse_args();z=np.load(args.source)
    words=z['words'].astype(np.int64);w=z['w'].astype(np.float64)
    H2=z['H2'].astype(np.float64);edges=z['tree_edges']
    m=Model(Ref());m.set_vectors(decode(words,edges));before=m.metrics(w,H2)
    show('newly refreshed starting point',before);start=time.time()
    repair=HRepair(m,w,H2,t_err=.0199986,margin=2e-7)
    H2n,result=repair.solve(maxiter=args.maxiter);after=m.metrics(w,H2n)
    show('bounded H2 probe MODEL ONLY',after)
    rec={'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
         'real_word_prefix_sha256':hashlib.sha256(words.astype(np.uint8).tobytes()).hexdigest(),
         'before_model':before,'after_model':after,'iterations':int(result.nit),
         'solver_message':str(result.message),'solver_success':bool(result.success),
         'seconds':time.time()-start,'word_changes':0,'two_body_weight_changes':0,
         'status':'UNQUALIFIED_MODEL_PROBE'}
    feasible=(max(after['error_1'],after['error_2'])<=.019999 and
              after['E_gap']>3.914898 and after['Lambda']>49 and
              after['lambda_eff']<=46.89422072083654)
    if feasible:
        measured=official(words,w,H2n,edges)
        rec['official_physical_metrics']=measured
        assert max(measured['error_1'],measured['error_2'])<=.019999
        assert measured['E_gap']>3.914898 and measured['gap_in_domain']
        assert measured['lambda_eff']<=46.89422072083654
        np.savez_compressed(args.output,words=words,w=w,H2=H2n,tree_edges=edges)
        rec['status']='UNQUALIFIED_OFFICIAL_PHYSICAL_SCREEN_ONLY'
        rec['output_sha256']=hashlib.sha256(args.output.read_bytes()).hexdigest()
        print('OFFICIAL_PHYSICAL',json.dumps(measured),flush=True)
    args.output.with_suffix('.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({k:rec[k]for k in ('status','iterations','solver_success','seconds')}),flush=True)


if __name__=='__main__':main()
