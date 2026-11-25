#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""C's h1-preserving free-sign/free-zero refit applied to a new word candidate.

Model feasibility is a screen only; official verification is always separate.
Candidate tree order is preserved. Reject an excessive initial one-body error
before spending a fit which cannot change that error.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from scipy.optimize import minimize
from fastchem import Ref, Model, decode
from exact_refit2 import Valley2
from pipeline import show


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('candidate',type=Path)
    ap.add_argument('output',type=Path)
    ap.add_argument('--outer',type=int,default=4)
    ap.add_argument('--inner',type=int,default=1200)
    ap.add_argument('--nu',type=float,default=75.)
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    with np.load(args.candidate) as c:
        W,w,H2=c['words'].astype(np.int64),c['w'].astype(np.float64),c['H2'].astype(np.float64)
        edges=c['tree_edges'] if 'tree_edges' in c.files else np.load(root/'baseline_C/submission.npz')['tree_edges']
    ref=Ref();m=Model(ref);m.set_vectors(decode(W,edges));t0=time.time()
    initial=m.metrics(w,H2);show('initial',initial)
    assert initial['error_1']<=.019999, 'One-body gate cannot be repaired by this h1-preserving fit'
    vy=Valley2(m,w,H2,t_err2=.0199986,margin=2e-7)
    x=vy.x0;nu=args.nu;rho=1e4;best=None;history=[]
    for j in range(args.outer):
        fit=minimize(vy.fun,x,args=(nu,rho),jac=True,method='L-BFGS-B',bounds=vy.bounds,
                     options={'maxiter':args.inner,'maxfun':3*args.inner,'maxcor':20,'ftol':1e-15,'gtol':1e-10})
        x=fit.x;vy.fun(x,nu,rho);lam2,E2,c=vy.last
        wb,hb,_=vy.build(x);ex=m.metrics(wb,hb)
        show(f'outer{j} nu{nu:.5f} rho{rho:.3g} c{c:+.3e} it{fit.nit} sec{time.time()-t0:.1f}',ex)
        history.append({'outer':j,'nu':nu,'rho':rho,'c':c,'iterations':fit.nit,'metrics':ex,
                        'message':str(fit.message),'seconds':time.time()-t0})
        feasible=ex['error_1']<=.019999 and ex['error_2']<=.0199988 and ex['E_gap']>3.914898
        if feasible and (best is None or ex['lambda_eff']<best):
            best=ex['lambda_eff']
            np.savez(args.output,words=W,w=wb,H2=hb,tree_edges=edges)
            print('KEPT_MODEL_FEASIBLE',best,flush=True)
        np.savez(args.output.with_name(args.output.stem+'_last.npz'),words=W,w=wb,H2=hb,tree_edges=edges)
        args.output.with_suffix('.json').write_text(json.dumps({'initial':initial,'history':history,
                       'best_lambda_eff':best,'status_scope':'Model-only; not a qualified package'},indent=2)+'\n')
        nu+=rho*c;rho=min(rho*4,1e8)


if __name__=='__main__':main()
