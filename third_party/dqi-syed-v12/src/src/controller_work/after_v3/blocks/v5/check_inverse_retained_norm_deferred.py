#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-only native test of matched retained-norm inverse debts.

The prefix panel is value-only with a declared open six-bit phase debt.
The paired panel checks every phase, including nonlinear probes and both
actual HMR masks. Classical copies only observe the real mask outcomes.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
RETAINED=865
PROBE_T=3
SEEDS=(59191,60191,61191)
MODES=('base_axis','extension_axis','equal_halves','arbitrary_K24','zero_source')
km=np=Candidate=Arithmetic=bit_matrix=None


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def mul(a,b):
    a,b,result=int(a),int(b),0
    while b:
        if b&1:result^=a
        b>>=1;a<<=1
        if a&4096:a^=0x1053
    return result


def inv(a):
    result,a,power=1,int(a),4094
    while power:
        if power&1:result=mul(result,a)
        a=mul(a,a);power>>=1
    return result


def inverse24(value):
    a,b=int(value)&4095,int(value)>>12
    reciprocal=inv(mul(a,a)^mul(a,b)^mul(2048,mul(b,b)))
    return mul(a^b,reciprocal)|(mul(b,reciprocal)<<12)


def fixtures(per_mode):
    rng=np.random.default_rng(202611111903)
    count=len(MODES)*per_mode
    values=rng.integers(0,1<<24,count,dtype=np.int64)
    axis=np.arange(per_mode,dtype=np.int64)
    values[:per_mode]=axis
    values[per_mode:2*per_mode]=axis<<12
    values[2*per_mode:3*per_mode]=axis|(axis<<12)
    values[4*per_mode:]=0
    inverses=np.array([inverse24(value) for value in values],dtype=np.int64)
    probes=rng.integers(0,1<<24,count,dtype=np.int64)
    dirty=rng.integers(0,2,(RETAINED-48,count),dtype=np.int8).astype(bool)
    phase=np.array([(int(m)&int(v)).bit_count()&1 for m,v in zip(probes,inverses)],dtype=bool)
    phase^=((inverses&1)!=0)&((inverses&(1<<13))!=0)&dirty[0]
    phase^=((inverses&4)!=0)&((inverses&(1<<17))!=0)&dirty[1]
    phase^=((inverses&16)!=0)&((inverses&(1<<21))!=0)&dirty[2]
    arrays=dict(source=bit_matrix(values,24),probe=bit_matrix(probes,24),
        clean=np.zeros((24,count),dtype=bool),dirty=dirty)
    return arrays,bit_matrix(inverses,24),phase


class ObserveChildNormReset:
    """Fixture-only classical readout of the actual child-norm HMR masks."""
    def __init__(self,builder,clean,observed):
        self.builder=builder;self.clean=tuple(clean[12:18]);self.observed=observed;self.calls=0

    def __getattr__(self,name):return getattr(self.builder,name)

    def hmr(self,source,mask):
        self.builder.hmr(source,mask)
        if tuple(source)==self.clean:
            assert len(mask)==6 and 6*(self.calls+1)<=len(self.observed)
            self.builder.cx(mask,self.observed[6*self.calls:6*(self.calls+1)])
            self.calls+=1


def build(kind):
    assert kind in ('matched_prefix','matched_pair')
    b=km.CircuitBuilder();b.set_max_qubits(889)
    source=b.create_quantum_register(24,'source')
    probe=b.create_classical_register(24,'probe')
    clean=b.create_quantum_register(24,'clean')
    dirty=b.create_quantum_register(RETAINED-48,'dirty')
    returns=int(kind=='matched_pair')
    observed=b.create_classical_register(6*(1+returns),'cleanup_masks')
    spy=ObserveChildNormReset(b,clean,observed)
    record=Candidate.inverse_prefix_with_bank(spy,source,clean)
    assert isinstance(record,Candidate.PrefixRecord) and not record.closed
    assert record.builder_id==id(spy) and record.source==tuple(source)
    assert record.prefix_static_T==191 and record.child_mask_bits==len(record.child_mask)==6
    b.cz(probe,source)
    b.ccz(source[0],source[13],dirty[0])
    b.ccz(source[2],source[17],dirty[1])
    b.ccz(source[4],source[21],dirty[2])
    receipts=[]
    if returns:
        receipts.append(Candidate.inverse_return_with_bank(spy,source,clean,record))
    assert record.closed==bool(returns) and spy.calls==1+returns
    assert all(row==dict(inverse_static_T=195,retained_storage_bits=24,
        original_norm_bits=12,child_norm_bits=6,child_inverse_bits=6,
        scalar_inverse_phase_static_T=4,maximum_additional_helpers=24,
        all_owned_storage_bits_reset=True,deferred_prefix_mask_paid=True) for row in receipts)
    static=191+195*returns
    assert b.num_allocated_qubits==RETAINED
    circuit=b.finish_circuit()
    assert circuit.operation_statistics().num_toffoli_like==static+PROBE_T
    assert circuit.num_qubits==RETAINED+24
    return circuit,dict(component_static_T=static,probe_T=PROBE_T,
        circuit_static_T=static+PROBE_T,Q=circuit.num_qubits,retained_Q=RETAINED,
        separately_owned_clean_bits=24,additional_helpers=24,child_norm_masks=1+returns,
        return_mask_positions=[1] if returns else [],
        prefix_mask_paid_at_matching_return=bool(returns),
        phase_checked=bool(returns),pending_prefix_phase_mask_bits=0 if returns else 6,
        stack_receipts=receipts,fixture_only_mask_copy_is_classical_Clifford=True)


def simulate(circuit,arrays,expected,phase,seed,metrics):
    count=arrays['dirty'].shape[1]
    sim=km.Simulator(batch_size=count,seed=seed,counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name,value in arrays.items():sim.write_across_shots(circuit.register_data[name],value)
    sim.write_across_shots(circuit.register_data['cleanup_masks'],
        np.zeros((6*metrics['child_norm_masks'],count),dtype=bool))
    sim.do(circuit)
    errors={}
    for name,value in expected.items():
        ids=np.flatnonzero(np.any(sim.read_across_shots(circuit.register_data[name])!=value,axis=0)).tolist()
        if ids:errors[name]=ids
    scratch_bad=bool(sim.read_across_shots([km.q(i) for i in range(RETAINED,circuit.num_qubits)]).any())
    phase_bad=(np.flatnonzero(sim.read_phase_flipped_across_shots()!=phase).tolist()
               if metrics['phase_checked'] else None)
    masks=sim.read_across_shots(circuit.register_data['cleanup_masks'])
    zeros=[int(np.count_nonzero(~np.any(masks[6*i:6*(i+1)],axis=0)))
           for i in range(metrics['child_norm_masks'])]
    expected_T=count*metrics['circuit_static_T']-4*sum(zeros[i] for i in metrics['return_mask_positions'])
    actual_T=sim.operation_statistics().num_toffoli_like
    row=dict(seed=seed,cases=count,value_error_case_ids=errors,scratch_errors=scratch_bad,
        phase_checked=metrics['phase_checked'],phase_error_case_ids=phase_bad,
        observed_zero_cleanup_masks_by_call=zeros,
        total_T=actual_T,independent_mask_exact_total_T=expected_T,
        measured_mean_T_excluding_probes=actual_T/count-PROBE_T)
    assert not errors and not scratch_bad and not phase_bad and actual_T==expected_T,row
    del sim;gc.collect()
    return row


def rejection_panel():
    rejected=[]
    for kind in ('source_length','bank_length','bank_alias','classical_bank','wrong_extension'):
        b=km.CircuitBuilder();source=b.create_quantum_register(24,'source');clean=b.create_quantum_register(24,'clean')
        kwargs={}
        if kind=='source_length':source=source[:23]
        if kind=='bank_length':clean=clean[:23]
        if kind=='bank_alias':clean=km.array([source[0],*clean[1:]])
        if kind=='classical_bank':clean=b.create_classical_register(24,'classical_bank')
        if kind=='wrong_extension':kwargs['delta']=1
        try:Candidate.inverse_prefix_with_bank(b,source,clean,**kwargs)
        except (ValueError,TypeError):rejected.append(kind)
        else:raise AssertionError(('invalid contract accepted',kind))
        assert b.num_allocated_qubits==48 and b.finish_circuit().operation_statistics().num_toffoli_like==0
    for kind in ('closed_record','wrong_builder','wrong_source','wrong_extension'):
        b=km.CircuitBuilder();source=b.create_quantum_register(24,'source')
        clean=b.create_quantum_register(24,'clean');mask=b.create_classical_register(6,'debt')
        record=Candidate.PrefixRecord(id(b),tuple(source),2048,mask)
        if kind=='closed_record':record.closed=True
        if kind=='wrong_builder':record.builder_id=-1
        if kind=='wrong_source':record.source=tuple(reversed(source))
        if kind=='wrong_extension':record.delta=1
        try:Candidate.inverse_return_with_bank(b,source,clean,record)
        except (ValueError,TypeError):rejected.append('return_'+kind)
        else:raise AssertionError(('invalid return record accepted',kind))
        assert b.num_allocated_qubits==48 and b.finish_circuit().operation_statistics().num_toffoli_like==0
    return rejected


def main():
    global km,np,Candidate,Arithmetic,bit_matrix
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--per-mode',type=int,default=4096)
    parser.add_argument('--keep-circuits',action='store_true')
    args=parser.parse_args()
    assert __debug__ and sys.version_info[:2]==(3,13) and 1<=args.per_mode<=4096
    args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'report.json').exists()
    sys.path.insert(0,str(PROJECT/'integration_v4'))
    import v4_pipeline as V4
    from v4_binding import verify_preservation
    V4.configure();before=verify_preservation(V4.Runtime)
    sys.path.insert(0,str(HERE))
    km=importlib.import_module('kickmix');np=importlib.import_module('numpy')
    Candidate=importlib.import_module('inverse_retained_norm_deferred');Arithmetic=Candidate.Arithmetic
    assert Arithmetic is V4.P.Arithmetic
    assert Path(Candidate.Cubic.__file__).resolve()==WORK/'work/round2/milestone152/source/cubic_inverse130.py'
    assert Path(Candidate.Scalar.__file__).resolve()==WORK/'work/round2/milestone152/source/scalar_inverse_phase.py'
    bit_matrix=importlib.import_module('quantum_reciprocal').bit_matrix
    from accepted_runtime import loaded_sources
    arrays,inverses,phase=fixtures(args.per_mode)
    pins={str(Path(module.__file__).resolve()):digest(module.__file__)
          for module in (Candidate,Candidate.Cubic,Candidate.Scalar,Arithmetic)}
    report=dict(status='IN_PROGRESS_MATCHED_RETAINED_NORM_INVERSES',rows=[],
        per_mode=args.per_mode,cases=len(MODES)*args.per_mode,modes=list(MODES),seeds=list(SEEDS),
        full_subfield_axes=args.per_mode==4096,
        full_norm_range_on_base_axis=args.per_mode==4096,
        source_sha256=pins,rejected_contracts=rejection_panel(),
        caller_owned_clean_bank_bits=24,arbitrary_dirty_bank_supported=False,
        fixture_mask_observation='Only an extra classical CX copies the actual HMR mask; no outcome is changed.',
        production_or_official_checked=False)
    def save():
        tmp=args.output/'report.json.tmp';tmp.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');tmp.replace(args.output/'report.json')
    started=time.monotonic();save()
    for kind in ('matched_prefix','matched_pair'):
        paths=[args.output/f'{kind}-{label}.kmb' for label in ('a','b')]
        circuit,metrics=build(kind);circuit.to_file(paths[0],format='kmb');circuit_sha=digest(paths[0])
        expected=dict(arrays)
        if kind=='matched_prefix':expected['source']=inverses
        runs=[simulate(circuit,arrays,expected,phase,seed,metrics) for seed in SEEDS]
        del circuit;gc.collect()
        again,again_metrics=build(kind);again.to_file(paths[1],format='kmb')
        assert again_metrics==metrics and digest(paths[1])==circuit_sha
        del again;gc.collect()
        report['rows'].append(dict(panel=kind,metrics=metrics,runs=runs,
            circuit_sha256=circuit_sha,two_identical_builds=True));save()
        print(json.dumps(dict(stage='panel_passed',panel=kind,metrics=metrics)),flush=True)
        if not args.keep_circuits:
            for path in paths:path.unlink()
    V4.assert_bindings();assert before==verify_preservation(V4.Runtime)
    assert pins=={path:digest(path) for path in pins}
    report.update(status='PASS_MATCHED_K24_INVERSES_WITH_RETAINED_NORM_DEBTS_COMPONENT',
        elapsed_seconds=time.monotonic()-started,loaded_sources=loaded_sources(),
        accepted_and_frozen_v4_sources_unchanged=True,
        source_expectation_per_pair='386-4/64',
        prefix_value_only_with_open_six_bit_phase=True,
        production_carry_storage_seam_requires_separate_physical_key_gate=True)
    save();print(json.dumps(dict(status=report['status'],elapsed_seconds=report['elapsed_seconds'])),flush=True)
    return 0


WORK=PROJECT.parent

if __name__=='__main__':
    raise SystemExit(main())
