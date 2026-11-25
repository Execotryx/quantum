#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Exact composition with affine classical parity and four fixed branches."""
from pathlib import Path
import hashlib
import importlib.util
import json
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
NARROW = HERE.parents[3]
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
for pin in json.loads((HERE/'INPUTS.json').read_text())['files']:
    data=(NARROW/pin['path']).read_bytes()
    assert len(data)==pin['bytes']
    assert hashlib.sha256(data).hexdigest()==pin['sha256'],pin['path']


def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,PARENT/relative)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


inverse_module=load('_rn2df_private_eight_inverse','normalization_eight_metadata/study_v2.py')
forward_module=load('_rn2df_private_parity_forward','normalization_phase_parity/study.py')
old,km=forward_module.old,forward_module.km


class CombinedBuilder(inverse_module.BranchBuilder):
    def cx(self,a,target):
        if isinstance(target,km.b):
            assert not self.stack and isinstance(a,km.b)
            am,ac=self.classical[a]
            bm,bc=self.classical[target]
            self.classical[target]=(am^bm,ac^bc)
        else:
            super().cx(a,target)

    def _condition(self,extra=None):
        conditions=set(self.stack)
        if extra is not None:
            conditions.add(extra)
        symbolic=set()
        for bit in conditions:
            mask,constant=self.classical[bit]
            if mask==0:
                if not constant:
                    return False,set()
            else:
                symbolic.add((mask,constant))
        # Only one nonconstant affine condition remains after fixed branches.
        # A nonzero affine parity is uniform; its original symbols are expanded
        # individually by _phase below rather than replaced by a fresh variable.
        assert len(symbolic)<=1
        return True,symbolic

    def _phase(self,value,extra=None):
        active,symbolic=self._condition(extra)
        if not active:
            return
        if not symbolic:
            self.phases[None]=self.phases.get(None,0)^value
            return
        mask,constant=next(iter(symbolic))
        if constant:
            self.phases[None]=self.phases.get(None,0)^value
        while mask:
            low=mask&-mask
            symbol=low.bit_length()-1
            self.phases[symbol]=self.phases.get(symbol,0)^value
            mask^=low


def prove(source,full,valid,branch,*,omit_final_helper_fix=False):
    builder=CombinedBuilder(full,valid,branch)
    x=list(builder.alloc_qubits(22))
    flags=list(builder.alloc_qubits(4))
    for q,value in zip(x,source):
        builder.values[q]=value
    forward_module.forward(builder,x,flags)
    expected=[0]*22
    expected_flags=[0]*4
    for k in range(11):
        lo=1<<(20-2*k)
        hi=min(old.MAX_X+1,1<<(22-2*k))
        support=(1<<hi)-(1<<lo)if hi>lo else 0
        for bit in range(2*k,22):
            expected[bit]^=support&source[bit-2*k]
        for bit in range(4):
            if(k>>bit)&1:
                expected_flags[bit]^=support
    assert all((builder.value(q)^value)&valid==0 for q,value in zip(x,expected))
    assert all((builder.value(q)^value)&valid==0 for q,value in zip(flags,expected_flags))
    assert builder.num_allocated_qubits==26 and builder.measurements==20
    builder.check_phase()
    forward_E=float(builder.count)
    fp=builder.peak
    builder.peak=26
    inverse_module.inverse(builder,x,flags,omit_final_helper_fix=omit_final_helper_fix)
    assert all((builder.value(q)^value)&valid==0 for q,value in zip(x,source))
    assert all(builder.value(q)&valid==0 for q in flags)
    assert builder.num_allocated_qubits==26
    unpaid=[key for key,value in builder.phases.items()if value&valid]
    if omit_final_helper_fix:
        assert branch[1]==1 and len(unpaid)==1
    else:
        builder.check_phase()
    return dict(branch=dict(mB=branch[0],m3=branch[1]),forward_E=forward_E,
                inverse_E=float(builder.count)-forward_E,total_E=float(builder.count),
                modeled_forward_peak=fp,modeled_inverse_peak=builder.peak,
                static_HMR_events=builder.measurements,
                active_independent_HMR_symbols=builder.active_symbols,
                inactive_helper_measurements=builder.inactive_measurements,
                all_data_and_owner_order_restored=True,all_scratch_flags_zero=True,
                unpaid_HMR_symbols=unpaid)


def main():
    began=time.monotonic()
    full=(1<<(1<<22))-1
    valid=(1<<(old.MAX_X+1))-2
    source=old.input_truths()
    rows=[prove(source,full,valid,b)for b in((0,0),(1,0),(0,1),(1,1))]
    negative=prove(source,full,valid,(0,1),omit_final_helper_fix=True)
    assert all(r['forward_E']==51.5 and r['modeled_forward_peak']==46 and r['modeled_inverse_peak']==30 for r in rows)
    inverse_E=sum(r['inverse_E']for r in rows)/4
    total=sum(r['total_E']for r in rows)/4
    assert(inverse_E,total)==(43.25,94.75)
    result=dict(status='PASS_COMPLETE_NORMALIZATION9475_PAPER_COMPOSITION_NOT_NATIVE',
                original_inputs_per_selected_branch=old.MAX_X,
                selected_original_HMR_outcomes=['B','T3'],selected_branch_weights=[0.25]*4,
                forward_parity_expanded_into_original_symbols=True,
                all_other_active_HMR_symbols_independent=True,rows=rows,
                negative_omitted_helper_fix=negative,forward_E=51.5,inverse_E=inverse_E,total_E=total,
                modeled_forward_peak=46,modeled_inverse_peak=30,external_boundary_owners=26,
                complete_Q=48,complete_expected_Toffolis_vs_candidate09=1566.75,T=4,R=33,
                unchanged_rotation_charge=230.84805946161188,
                complete_expected_cost=48*(1566.75+1+230.84805946161188),
                normalization_T=0,normalization_R=0,numeric_error_change=0,
                protected_phase_loaders_endpoint_unchanged=True,
                native_execution=False,official_execution=False,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                inputs_sha256=hashlib.sha256((HERE/'INPUTS.json').read_bytes()).hexdigest(),
                seconds=time.monotonic()-began,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    with(HERE/'study.json').open('x')as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
