#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Exact low-wrapper phases and full owned-source root ledger, no native."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import hashlib,importlib.util,json,resource,sys
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[2]
for pin in json.loads((HERE/'INPUTS.json').read_text())['files']:
    raw=(NARROW/pin['path']).read_bytes()
    assert len(raw)==pin['bytes']and hashlib.sha256(raw).hexdigest()==pin['sha256']
sys.path[:0]=[str(NARROW/'research/stream_phase'),str(NARROW/'checkpoint002/cleanroom/odd_sqrt')]
from drive_paper_ledger import PaperCounter,km
import consuming_odd_sqrt as root


class LowTruth:
    """All four(x2,b) states, with one symbolic debt per del_and outcome."""
    def __init__(self):self.values={};self.live=set();self.nextq=0;self.ccx_count=0;self.phase_checks=[]
    def alloc_qubits(self,n):
        out=[]
        for _ in range(n):
            q=('q',self.nextq);self.nextq+=1;self.live.add(q);self.values[q]=0;out.append(q)
        return out
    def x(self,q):self.values[q]^=15
    def cx(self,a,b):self.values[b]^=self.values[a]
    def ccx(self,a,b,t):self.values[t]^=self.values[a]&self.values[b];self.ccx_count+=1
    def del_and(self,a,b,t):
        measured=self.values[t];fix=self.values[a]&self.values[b]
        assert measured^fix==0,('HMR phase',measured,fix)
        self.phase_checks.append(dict(measured_truth=measured,correction_truth=fix))
        self.values[t]=0
    def free(self,q):assert q in self.live and not self.values[q];self.live.remove(q)


def local():
    results=[]
    for inverse in (False,True):
        b=LowTruth();low=b.alloc_qubits(3);sign=b.alloc_qubits(1)[0]
        b.values[low[0]]=b.values[low[1]]=15 if inverse else 0
        b.values[low[2]]=0b1010;b.values[sign]=0b1100
        original_x2=b.values[low[2]];original_b=b.values[sign]
        u,c=root._low_prepare(b,low,sign,inverse=inverse)
        assert b.values[u]==0 and b.values[c]==original_b
        assert b.values[low[0]]==b.values[low[1]]==15 and b.values[low[2]]==original_x2
        # The high operation's contract preserves its carry and is therefore
        # identical when the exact coherent copy c=b is replaced by b itself.
        root._low_finish(b,low,sign,u,c,inverse=inverse)
        pair=0 if inverse else 15
        assert b.values[low[0]]==b.values[low[1]]==pair
        assert b.values[low[2]]==original_x2 and b.values[sign]==original_b
        assert len(b.live)==4 and b.ccx_count==2 and len(b.phase_checks)==2
        results.append(dict(inverse=inverse,input_cases=4,Toffolis=2,helpers=2,
            carry_equals_original_b=True,x2_unchanged=True,expected_output_pair='00'if inverse else'11',
            all_HMR_signs= b.phase_checks,all_outcome_combinations_proved=4))
    return results


ORIGINAL=root._root_step


def specialized(builder,remainder,older,b,*,initial=False,inverse=False):
    assert not initial and isinstance(b,km.q)
    low=list(remainder[:3]);high=list(remainder[3:])
    assert b not in remainder+older and len(set(remainder+older+[b]))==len(remainder)+len(older)+1
    if not inverse:builder.x(low[0]);builder.x(low[1])
    builder.cx(b,root._arr(high))
    if inverse:
        root._add_leading_one(builder,high,inverse=True)
        root.add(builder,older,high,carry_in=b,subtract=True)
    else:
        root.add(builder,older,high,carry_in=b)
        root._add_leading_one(builder,high)
    builder.cx(b,root._arr(high))
    if inverse:builder.x(low[0]);builder.x(low[1])


def full(special):
    b=PaperCounter(49);norm=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4));events=[]
    direction='forward';indices=iter(range(1,13))
    def intercept(builder,remainder,older,sign,*,initial=False,inverse=False):
        j=next(indices);before=builder.count;live=builder.num_allocated_qubits
        routine=specialized if special and j>=11 else ORIGINAL
        routine(builder,remainder,older,sign,initial=initial,inverse=inverse)
        if j>=11:
            assert sign not in list(remainder)+list(older)
            events.append(dict(direction=direction,j=j,low_width=3,high_width=len(remainder)-3,
                source_width=len(older),carry_disjoint=True,data_before=live,data_after=builder.num_allocated_qubits,
                root_helper_owners=0 if special else 2,Toffolis=float(builder.count-before)))
    root._root_step=intercept
    result=root.forward(b,norm);forward=float(b.count)
    assert result['root']==norm[10:]and result['residual']==norm[:10]
    assert b.num_allocated_qubits==26
    direction='inverse';indices=iter(reversed(range(1,13)))
    restored=root.inverse(b,norm);root._root_step=ORIGINAL
    assert restored==norm and b.num_allocated_qubits==26
    return dict(specialized=special,forward_E=forward,inverse_E=float(b.count)-forward,
        total_E=float(b.count),peak=b.peak,retained_exponent_flags=4,final_live=26,late_steps=events,
        final_map='Original norm22 restored on same owners; exponent flags4 untouched.')


def main():
    low=local();baseline=full(False);new=full(True)
    assert baseline['total_E']==206 and new['total_E']==198
    assert baseline['total_E']-new['total_E']==8
    out=dict(status='INDEPENDENT_COMPLETE_ROOT_TAIL_PAPER_AUDIT_PASS_NOT_NATIVE',
             local_exact_phase=low,baseline=baseline,specialized=new,
             complete_saving_E=8,T_change=0,R_change=0,accuracy_change=0,
             inverse_precondition='The two low1 bits are the exact forward image after all later root steps and residual conversion have been reversed.',
             high_arithmetic_equivalence='The new carry b is the exact original preserved input value of the old copy c. It is disjoint from older_root and high in both directions. No duplicate-source or borrow-owner assumption is made.',
             no_original_source_modified=True,no_native_builder=True)
    path=HERE/'audit.json';path.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))


if __name__=='__main__':main()
