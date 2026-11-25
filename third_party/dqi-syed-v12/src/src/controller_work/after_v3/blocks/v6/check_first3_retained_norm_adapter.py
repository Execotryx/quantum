#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-only production-key gate for the zero-repaired third public chart.

The original physical corpus and exclusions remain. One deterministic
old-admitted physical zero-residue fixture is added. The independent boundary
oracle checks every unchanged head/flag and replays the new common carry
scale. Both constant-carry seams and the initial tail-bit reset are checked.
The old arbitrary-initial-carry component ABI is not borrowed as clean.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORK = PROJECT.parent
ROOT = WORK.parent
DEFAULT_FIXTURES = WORK/'night_c27/arithmetic/panel_audit/prepared/cases.json'
RARE_FIXTURES = WORK/'after_c5/arithmetic_t/runs/first2-physical-gauge1/cases.json'
ZERO_FIXTURES = HERE/'runs/third-raw-zero/cases.json'
PREFIX_T = 101058-3+32
KEY_T = 217229-301
SEEDS = (147,1147,2147)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def atomic_json(path,value):
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    tmp.replace(path)


def load_harness():
    path=WORK/'night_c27/arithmetic/panel_audit/check_key_boundary.py'
    sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location('third_chart_unchanged_key_harness',path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module,path


def build(V4,Adapter,Phase,events,harness,label,paths):
    import kickmix as km
    events.rows.clear()
    b=km.CircuitBuilder()
    b.set_max_qubits(889)
    S=[b.create_quantum_register(12,f'S{i}') for i in range(70)]
    probe=b.create_classical_register(865,'boundary_probe')
    seam_capture=[]
    prefix_seam_capture=[]
    key=None
    def stage(message):
        if message=='first_three_prefix_carry_restored':
            assert key is None and not prefix_seam_capture
            assert b.num_allocated_qubits==865
            seam=b.finish_circuit()
            seam.to_file(paths['prefix_seam'],format='kmb')
            prefix_seam_capture.append(dict(circuit_sha256=digest(paths['prefix_seam']),
                Q=seam.num_qubits,retained_Q=865,
                initially_zero_tail_flag_index=864))
            del seam
            gc.collect()
        if message=='first_three_clean_carry_seam':
            assert key is not None and not seam_capture
            assert b.num_allocated_qubits==864
            assert key['extraction'].clean_carry_seam_reached
            assert key['extraction'].closed_inverse_calls==0
            seam=b.finish_circuit()
            seam.to_file(paths['seam'],format='kmb')
            index_map={km.q(index):index for index in range(seam.num_qubits)}
            seam_capture.append(dict(circuit_sha256=digest(paths['seam']),
                Q=seam.num_qubits,retained_Q=864,
                carry_indices=[index_map[wire] for wire in key['carry']]))
            del seam
            gc.collect()
        if isinstance(message,str) and message.endswith(('04','09','14','19','24','29','34','00')):
            print(json.dumps(dict(build=label,stage=message)),flush=True)
    key=V4.emit_key_prefix(b,S,j_min=15,stage=stage)
    assert isinstance(key['extraction'],Adapter.ProductionRecord)
    assert key['extraction'].declared_initial_carry==1
    assert len(prefix_seam_capture)==1
    assert all(isinstance(rec,Phase.PrefixRecord) and not rec.closed
        and rec.prefix_static_T==191 and rec.child_mask_bits==6
        for rec in key['extraction'].first_inverses)
    third=key['extraction'].third
    assert isinstance(third,Adapter.Third.Record) and not third.closed
    assert third.prefix_static_T==620 and len(third.zero_mask)==1
    assert len(third.inverses)==3 and all(isinstance(rec,Phase.PrefixRecord)
        and not rec.closed and rec.prefix_static_T==191 for rec in third.inverses)
    boundary=km.array([*(q for word in key['N'] for q in word),
                       *(q for word in key['D'] for q in word),
                       *key['carry'][12:],key['gauge'].flag])
    assert len(boundary)==len(set(boundary))==865 and b.num_allocated_qubits==865
    front=b.finish_circuit()
    assert front.operation_statistics().num_toffoli_like==PREFIX_T
    assert front.num_qubits==889
    front.to_file(paths['prefix'],format='kmb')
    del front;gc.collect()
    b.cz(probe,boundary)
    for x,y,z in harness.TRIPLES:
        b.ccz(boundary[x],boundary[y],boundary[z])
    V4.emit_key_closing(b,key,stage=stage)
    rec=key['extraction']
    assert key['closed'] and rec.closed and b.num_allocated_qubits==840
    assert len(seam_capture)==1 and rec.clean_carry_seam_reached
    assert rec.closed_inverse_calls==6 and len(rec.borrow_receipts)==6
    assert all(row==dict(inverse_static_T=195,retained_storage_bits=24,
        original_norm_bits=12,child_norm_bits=6,child_inverse_bits=6,
        scalar_inverse_phase_static_T=4,maximum_additional_helpers=24,
        all_owned_storage_bits_reset=True,deferred_prefix_mask_paid=True) for row in rec.borrow_receipts)
    assert rec.third.closed and rec.third.zero_mask is None
    assert rec.third_receipt['prefix_zero_mask_paid'] and rec.third_receipt['return_zero_flag_retired']
    assert rec.third_receipt['return_static_T']==654 and rec.third_receipt['closed_inverse_calls']==3
    circuit=b.finish_circuit()
    assert circuit.operation_statistics().num_toffoli_like==KEY_T+len(harness.TRIPLES)
    assert circuit.num_qubits==889
    circuit.to_file(paths['pair'],format='kmb')
    indices={km.q(i):i for i in range(circuit.num_qubits)}
    layout=[indices[wire] for wire in boundary]
    # Use the known native index mapping, not an undocumented wire property.
    seam_capture[0]['carry_indices']=[indices[wire] for wire in key['carry']]
    prefix_seam_capture[0]['carry_indices']=[indices[wire] for wire in key['carry']]
    assert prefix_seam_capture[0]['carry_indices']==list(range(840,864))
    expectation=events.snapshot(KEY_T)
    rows=Counter(events.rows)
    expected_events=Counter({
        ('direct_carry84_selected_target_parities',84,24):32,
        ('inverse_phase27_12_helpers',27,12):66,
        ('last_return_child_norm_guard',15,6):1,
        ('scalar_inverse_six',4,6):7,
        ('tail_or_gauge_fresh_zero_phase',10,1):1,
        ('tail_or_gauge_fresh_zero_phase',22,1):21})
    assert rows==expected_events,(rows,expected_events)
    delta=-Fraction(1310167980,4194304)
    assert Fraction(expectation['expected_T_exact'])==Fraction(227544411715,1048576)+delta
    metrics=dict(key_pair_static_T=KEY_T,prefix_static_T=PREFIX_T,Q=889,
        probe_static_T=len(harness.TRIPLES),full_pair_static_T=KEY_T+len(harness.TRIPLES),
        exact_source_expectation=expectation,
        static_T_model_delta_from_v4=-301,
        exact_mean_delta_from_v4=str(delta),
        retained_carry_storage_bits=24,closed_inverse_calls=rec.closed_inverse_calls,
        borrow_receipts=rec.borrow_receipts,seam=seam_capture[0],
        prefix_seam=prefix_seam_capture[0],prefix_phase_debts_retired=6,
        third_zero_mask_retired=True,third_receipt=rec.third_receipt)
    del circuit,b;gc.collect()
    return metrics,layout


def simulate_seam(args,path,carry_indices,cases,report,*,prefix=False):
    import kickmix as km
    import numpy as np
    circuit=km.Circuit.from_file(str(path),format='kmb')
    registers=circuit.register_data
    syndrome_register=km.array([wire for i in range(70) for wire in registers[f'S{i}']])
    probe_register=registers['boundary_probe']
    for seed in args.seeds:
        for start in range(0,len(cases),args.batch_size):
            rows=cases[start:start+args.batch_size]
            values=np.asarray([row['syndromes'] for row in rows],dtype=np.int64)
            values=((values[:,:,None]>>np.arange(12))&1).astype(bool).reshape(len(rows),840).T
            probes=np.random.default_rng(seed*100000+start).integers(0,2,
                (865,len(rows)),dtype=np.int8).astype(bool)
            sim=km.Simulator(batch_size=len(rows),seed=seed+start,counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(syndrome_register,values)
            sim.write_across_shots(probe_register,probes)
            sim.do(circuit)
            actual=sim.read_across_shots([km.q(index) for index in carry_indices])
            expected=np.zeros((24,len(rows)),dtype=bool);expected[0]=True
            wrong=np.flatnonzero(np.any(actual!=expected,axis=0)).tolist()
            mask_bad=np.flatnonzero(np.any(sim.read_across_shots(probe_register)!=probes,axis=0)).tolist()
            # The prefix also owns its untouched initial zero tail flag; the return has closed it.
            retained=865 if prefix else 864
            scratch_ids=[km.q(index) for index in range(retained,circuit.num_qubits)]
            scratch_bad=bool(sim.read_across_shots(scratch_ids).any())
            tail_bad=bool(sim.read_across_shots([km.q(864)]).any()) if prefix else False
            result=dict(panel='prefix_public_carry_seam' if prefix else 'return_public_carry_seam',
                seed=seed,start=start,shots=len(rows),
                constant_carry_error_case_ids=wrong,probe_error_case_ids=mask_bad,
                scratch_errors=scratch_bad,initial_tail_flag_error=tail_bad,phase_checked=False,
                phase_scope='Special prefix HMR debts are intentionally still open')
            assert not wrong and not mask_bad and not scratch_bad and not tail_bad,result
            report['seam_runs'].append(result)
            del sim;gc.collect()
    del circuit;gc.collect()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--keep-circuits',action='store_true')
    parser.add_argument('--zero-fixtures',type=Path,default=ZERO_FIXTURES)
    parser.add_argument('--require-gauge1',action='store_true')
    args=parser.parse_args()
    assert __debug__ and sys.version_info[:2]==(3,13) and args.batch_size>0
    assert not (args.output/'report.json').exists()
    args.output.mkdir(parents=True,exist_ok=True)
    args.fixtures_file=DEFAULT_FIXTURES
    args.extra_fixtures=[RARE_FIXTURES,args.zero_fixtures]
    preparation_path=args.zero_fixtures.with_name('report.json')
    preparation=json.loads(preparation_path.read_text())
    assert preparation['status']=='PREPARED_ADMITTED_PHYSICAL_THIRD_RAW_ZERO_FIXTURE_NOT_NATIVE'
    assert preparation['cases']==1 and preparation['new_population_draws']==0
    assert preparation['prepared_cases_sha256']==digest(args.zero_fixtures)
    assert preparation['unchanged_complete_classifier_admitted'] and preparation['exact_C5_raw_query_zero']
    fixed_inputs={
        DEFAULT_FIXTURES:'eb9216d25bd69f17179533932f0ec6a8704860a366117bd370b6eec35495e339',
        RARE_FIXTURES:'149d50ccac0d343e4479444f1804a01127be648750f12ed9a99b1acc04f5b3d4'}
    assert all(digest(path)==wanted for path,wanted in fixed_inputs.items())
    for relative,wanted in preparation['source_bindings'].items():
        assert digest(ROOT/relative)==wanted,relative
    args.weights=list(range(15,36));args.per_weight=1;args.start=0;args.count=None
    args.j_min=15;args.first_two_charts=args.nested_norm=True;args.seeds=list(SEEDS)
    sys.path.insert(0,str(PROJECT/'integration_v4'))
    import v4_pipeline as V4
    from v4_binding import verify_preservation
    V4.configure()
    before=verify_preservation(V4.Runtime)
    old_extractor=V4.P.Extractor
    sys.path.insert(0,str(HERE))
    import first3_retained_norm_adapter as Adapter
    import inverse_retained_norm_deferred as Phase
    assert Adapter.Base is old_extractor and Adapter.Arithmetic is V4.Last
    assert Adapter.A is Phase.Arithmetic is V4.P.Arithmetic
    # New public binding, with the frozen v4 arithmetic providers preserved.
    V4.P.Extractor=Adapter
    V4.assert_bindings()
    harness,harness_path=load_harness()
    import boundary_scale_first3 as Boundary
    rescale_boundary=Boundary.rescale_boundary
    from accepted_runtime import loaded_sources
    from v4_events import Events
    events=Events();events.install(V4)
    selected,excluded,old_oracles,partition=harness.load_cases(args)
    oracles=[rescale_boundary(row) for row in old_oracles]
    full_count=len(selected)
    assert full_count==783 and len(excluded)==76
    assert any(row['raw_queries'][2]==0 for row in old_oracles)
    assert all(row['third_chart']['raw_zero']==(old['raw_queries'][2]==0)
               for row,old in zip(oracles,old_oracles))
    if args.smoke:
        chosen={next(i for i,row in enumerate(selected) if row['weight']==j) for j in (15,16,35)}
        chosen.update(i for i,oracle in enumerate(oracles) if oracle['gauge']==1)
        chosen.update(i for i,oracle in enumerate(oracles) if oracle['third_chart']['raw_zero'])
        chosen=sorted(chosen)
        selected=[selected[i] for i in chosen]
        oracles=[oracles[i] for i in chosen]
        partition=dict(partition,complete_key_domain=False,smoke_selected_indices=chosen)
    assert all(row['changed_carry_variant']=='first3_zero_repaired' for row in oracles)
    assert any(row['third_chart']['raw_zero'] for row in oracles)
    if args.require_gauge1:
        assert any(row['gauge']==1 for row in oracles),'New carry gauge1 requires a real fixture; no old gauge label is reused'
    atomic_json(args.output/'fixtures.json',[dict(row,boundary_oracle=oracle)
                for row,oracle in zip(selected,oracles)])
    atomic_json(args.output/'explicit-key-domain-exclusions.json',excluded)
    pins={str(path.resolve()):digest(path) for path in
          (Path(__file__),Path(Adapter.__file__),Path(Adapter.Third.__file__),Path(Phase.__file__),
           Path(Boundary.__file__),harness_path,DEFAULT_FIXTURES,RARE_FIXTURES,
           args.zero_fixtures,preparation_path,HERE/'prepare_zero_third_fixture.py')}
    assert digest(Phase.__file__)=='8cb8eaee9312acc81a3048072ec3ddf721399ba8ccdd7eac94002f9d4ec2da46'
    report=dict(status='IN_PROGRESS_PRODUCTION_THIRD_ZERO_REPAIRED_CHART',runs=[],seam_runs=[],
        **partition,selected_cases=len(selected),full_available_cases=full_count,
        key_domain_exclusions=len(excluded),physical_weights=dict(Counter(row['weight'] for row in selected)),
        gauges=dict(Counter(row['gauge'] for row in oracles)),
        actual_new_gauge1_covered=any(row['gauge']==1 for row in oracles),
        physical_raw_zero_cases=sum(row['third_chart']['raw_zero'] for row in oracles),
        deterministic_zero_fixture_preparation=preparation,
        terminal_seed_flags=dict(Counter(row['terminal_seed_flag'] for row in oracles)),
        source_sha256=pins,production_initial_carry=1,
        arbitrary_initial_carry_extension_tested=False,
        old_arbitrary_initial_carry_component_unchanged=True,
        runtime_bindings=dict(V4.runtime_bindings(),
            production_special_inverse_provider=Phase.__name__,
            repaired_third_chart_provider=Adapter.Third.__name__,
            clean_carry_storage_indices=list(range(24)),
            prefix_classical_debt_bits=37,six_prefix_masks_paid_from_return_child=True,
            prefix_zero_mask_paid_at_return_predicate=True),
        limitations=['Only physical production inputs are used; no arbitrary carry is declared clean.',
                    'The prefix and public-carry seam have open HMR debts and are value-only panels.',
                    'The full paired key checks arbitrary diagonal and cubic probes plus all restoration.',
                    'The new final carry/gauge is independently replayed; old gauge1 labels do not imply new gauge1 coverage.',
                    'The added physical raw-zero fixture is a deterministic magnitude solve, not a population draw.',
                    'This is not a full decoder, official price, or new population experiment.'])
    atomic_json(args.output/'report.json',report)
    started=time.monotonic()
    paths={label:{kind:args.output/f'{kind}-{label}.kmb' for kind in ('prefix','pair','seam','prefix_seam')}
           for label in ('a','b')}
    try:
        metrics,layout=build(V4,Adapter,Phase,events,harness,'a',paths['a'])
        again,second_layout=build(V4,Adapter,Phase,events,harness,'b',paths['b'])
        assert metrics==again and layout==second_layout
        hashes={kind:digest(paths['a'][kind]) for kind in paths['a']}
        assert all(hashes[kind]==digest(paths['b'][kind]) for kind in hashes)
        report.update(metrics=metrics,boundary_physical_indices=layout,
            prefix_sha256=hashes['prefix'],pair_sha256=hashes['pair'],
            public_carry_seam_sha256=hashes['seam'],
            public_prefix_carry_seam_sha256=hashes['prefix_seam'],two_identical_builds=True)
        harness.simulate(args,paths['a']['prefix'],'prefix',layout,selected,oracles,report)
        harness.simulate(args,paths['a']['pair'],'pair',layout,selected,oracles,report)
        simulate_seam(args,paths['a']['seam'],metrics['seam']['carry_indices'],selected,report)
        simulate_seam(args,paths['a']['prefix_seam'],metrics['prefix_seam']['carry_indices'],selected,report,prefix=True)
        assert before==verify_preservation(V4.Runtime)
        V4.assert_bindings()
        assert V4.P.Extractor is Adapter and Adapter.Base is old_extractor
        assert pins=={path:digest(path) for path in pins}
        report.update(status='PASS_PRODUCTION_THIRD_ZERO_REPAIRED_CHART_KEY',
                      accepted_and_frozen_v4_sources_unchanged=True,
                      loaded_sources=loaded_sources(),preservation_and_component_gates=before)
    except BaseException as error:
        report.update(status='FAILED_OR_INTERRUPTED_PRODUCTION_THIRD_ZERO_REPAIRED_CHART_KEY',failure=repr(error))
        atomic_json(args.output/'report.json',report)
        raise
    report['elapsed_seconds']=time.monotonic()-started
    atomic_json(args.output/'report.json',report)
    if not args.keep_circuits:
        for group in paths.values():
            for path in group.values():path.unlink()
    print(json.dumps(dict(status=report['status'],cases=len(selected),
                         elapsed_seconds=report['elapsed_seconds'],metrics=report['metrics'])),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
