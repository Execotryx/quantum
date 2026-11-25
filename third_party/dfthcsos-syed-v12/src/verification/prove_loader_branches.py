#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Syed Asad Ali. Credits: Opus and Astra.
"""All-address, all-HMR-outcome proof for the supplied circuit instruction set.

Qubit values are packed Python-int truth tables over all 1220 legal addresses.
Each HMR introduces an independent symbolic measurement variable. Its phase
coefficient is the erased Boolean value; conditional CZ adds its two-control
product to the same coefficient. Every coefficient must vanish independently.
This proves all HMR branches, not just a sample, for each legal endpoint. The
previous-batch ruling is explicitly assumed. Unsupported operations reject.
"""
import sys,json,hashlib,re
from pathlib import Path
import numpy as np

def packed(values):
    return sum(int(x)<<i for i,x in enumerate(values))
def prove_one(path,words,k,start_current=False):
    text=Path(path).read_text();lines=text.splitlines();A=words.shape[0];mask=(1<<A)-1
    q=[0]*128;regs={};name={};ops=[];cost=0
    for line in lines:
        a=line.split()
        if not a:continue
        if a[0]=='APPEND_TO_REGISTER':regs.setdefault(a[2],[]).append(int(a[1][1:]));continue
        if a[0]=='REGISTER':name[a[1]]=a[2].strip('"');continue
        ops.append(a)
    reg={name[r]:qs for r,qs in regs.items()}
    for j,qi in enumerate(reg['selection']):q[qi]=packed(((np.arange(A)>>j)&1).tolist())
    src=k if start_current else k-1;dst=k-1 if start_current else k
    for j in range(5):
        values=words[:,5*src+j] if src>=0 else np.zeros(A,dtype=int)
        for b,qi in enumerate(reg[f'word_{j}']):q[qi]=packed(((values>>b)&1).tolist())
    selection_initial=[q[x] for x in reg['selection']]
    phase=[];cbits={};measurements=0
    for index,a in enumerate(ops):
        op=a[0];idx=[int(x[1:]) for x in a[1:] if x.startswith('q')]
        if op=='X':assert len(a)==2;q[idx[0]]^=mask
        elif op=='CX':assert len(a)==3;q[idx[1]]^=q[idx[0]]
        elif op=='CCX':assert len(a)==4;q[idx[2]]^=q[idx[0]]&q[idx[1]];cost+=1
        elif op=='R':
            assert len(a)==2
            assert q[idx[0]]==0,('reset_erases_information',path,index)
        elif op=='HMR':
            assert len(a)==3
            cbits[a[2]]=len(phase);phase.append(q[idx[0]]);q[idx[0]]=0;measurements+=1
        elif op=='CZ':
            assert len(a)==5 and a[3]=='if',('unsupported_phase',a)
            phase[cbits[a[4]]]^=q[idx[0]]&q[idx[1]]
        else:raise ValueError(('unsupported_instruction',a))
    assert all(p==0 for p in phase),('uncorrected_phase',path,k,start_current)
    assert selection_initial==[q[x]for x in reg['selection']]
    for j in range(5):
        values=words[:,5*dst+j] if dst>=0 else np.zeros(A,dtype=int)
        for b,qi in enumerate(reg[f'word_{j}']):assert q[qi]==packed(((values>>b)&1).tolist()),('wrong_word',path,k,j,b)
    owned=set(sum(reg.values(),[]))
    assert all(q[i]==0 for i in range(len(q)) if i not in owned),('uncleared_workspace',path)
    return {'loader':k,'direction':'current_to_previous' if start_current else 'previous_to_current',
            'addresses':A,'independent_HMR_variables':measurements,'all_phase_coefficients_zero':True,
            'toffoli_count':cost,'source_sha256':hashlib.sha256(text.encode()).hexdigest()}

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    sources=Path(sys.argv[1]) if len(sys.argv)>1 else root/'runtime_verify'/'decoded_kmx'
    npz=Path(sys.argv[2]) if len(sys.argv)>2 else root/'input'/'chem_pack'/'v14'/'submission.npz'
    out=Path(sys.argv[3]) if len(sys.argv)>3 else root/'refit'/'loader_all_branch_proof.json'
    words=np.load(npz)['angle_words']
    results=[prove_one(sources/f'angle_k_{k}.kmx',words,k,rev)for k in range(15)for rev in [False,True]]
    data={'status':'PASS','assumption':'Previous-batch ruling: each loader is required on its two legal endpoints.',
          'method':'Exact Boolean truth tables and independent symbolic HMR phase coefficients.',
          'circuits':15,'directions_per_circuit':2,'addresses':len(words),'all_HMR_outcomes':True,
          'angles_toffoli_per_pass':sum(x['toffoli_count']for x in results if x['direction']=='previous_to_current'),
          'checks':results}
    out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k!='checks'},indent=2))
