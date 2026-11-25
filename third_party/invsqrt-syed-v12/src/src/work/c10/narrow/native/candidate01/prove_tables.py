# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Native Q49 proof fixture for the own60/73 loaders and9E cleanup.

Run only inside the shared serial resource_guard slot. Component evidence is
explicitly separate from qualification by the official complete verifier.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import resource
import time

os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
from common import km,array,HERE,NARROW,MODEL_SHA,verify_gate_sources
from tables import TableDebts,load_joint16,cleanup_joint16,model_values,model_truths,PINS
from table_text_symbolic import prove_native_text
import numpy as np


def atomic_json(path,data):
    path=Path(path);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,indent=2)+'\n');os.replace(temp,path)


def bits(values,width):
    return ((values.astype(np.uint64)[None,:]>>np.arange(width,dtype=np.uint64)[:,None])&1).astype(bool)


def read(sim,wires):
    return (sim.read_across_shots(array(wires)).astype(np.uint64)<<np.arange(len(wires),dtype=np.uint64)[:,None]).sum(axis=0)


def build_single(variant):
    builder=km.CircuitBuilder();builder.set_max_qubits(49)
    address=list(builder.create_quantum_register(7,'address'))
    spectators=list(builder.create_quantum_register(19 if variant=='first' else 24,'spectators'))
    debts=TableDebts();A,H=load_joint16(builder,address,variant=variant,debts=debts)
    forward=builder.finish_circuit();pending=len(debts.pending)
    cleanup=cleanup_joint16(builder,address,A,H,debts);full=builder.finish_circuit()
    assert not debts.pending and builder.num_allocated_qubits==len(address)+len(spectators)
    assert full.num_qubits==49
    charge=60 if variant=='first' else 73
    return dict(builder=builder,address=address,spectators=spectators,
                cuts=[dict(name='loaded',circuit=forward,A=A,H=H,extras=[],Toffolis=charge,phase_zero=False),
                      dict(name='clean',circuit=full,A=[],H=[],extras=[],Toffolis=charge+9,phase_zero=True)],
                native_Q=49,helper_debts=pending,cleanup=cleanup)


def build_deferred():
    builder=km.CircuitBuilder();builder.set_max_qubits(49)
    address=list(builder.create_quantum_register(7,'address'))
    spectators=list(builder.create_quantum_register(19,'spectators'));debts=TableDebts()
    A1,H1=load_joint16(builder,address,variant='first',debts=debts);first=builder.finish_circuit()
    initial_helper_debts=len(debts.pending);truths=model_truths()
    for wire,truth in zip(A1+H1,list(truths['A'])+list(truths['H'][:3])):debts.erase(builder,wire,truth,free=True)
    # Five additional preserved spectator owners occupy exactly the first
    # pool's excess room before the second18-wire work pool is allocated.
    extras=list(builder.alloc_qubits(5))
    for source,target in zip(spectators[:5],extras):builder.cx(source,target)
    A2,H2=load_joint16(builder,address,variant='second',debts=debts);second=builder.finish_circuit()
    all_debts=len(debts.pending);cleanup=cleanup_joint16(builder,address,A2,H2,debts)
    for source,target in zip(spectators[:5],extras):builder.cx(source,target)
    builder.free(array(extras));full=builder.finish_circuit()
    assert full.num_qubits==49 and not debts.pending and builder.num_allocated_qubits==26
    return dict(builder=builder,address=address,spectators=spectators,
                cuts=[dict(name='first_loaded',circuit=first,A=A1,H=H1,extras=[],Toffolis=60,phase_zero=False),
                      dict(name='second_loaded_with_old_debts',circuit=second,A=A2,H=H2,extras=extras,Toffolis=133,phase_zero=False),
                      dict(name='all_debts_repaid',circuit=full,A=[],H=[],extras=[],Toffolis=142,phase_zero=True)],
                native_Q=49,first_helper_debts=initial_helper_debts,all_debts_before_cleanup=all_debts,cleanup=cleanup)


def prove_case(name,fixture,output):
    address=fixture['address'];spectators=fixture['spectators'];values=model_values();modelA=np.array(values['A'],dtype=np.uint64);modelH=np.array(values['H'],dtype=np.uint64)&7
    records=[];circuits=[];symbolic=[];began=time.monotonic()
    for cut in fixture['cuts']:
        circuit=cut['circuit'];statistics=circuit.operation_statistics()
        assert statistics.num_toffoli_like==cut['Toffolis'],(name,cut['name'],statistics.num_toffoli_like,cut['Toffolis'])
        path=output/f'{name}_{cut["name"]}.kmb';circuit.to_file(str(path),format='kmb')
        circuits.append(dict(cut=cut['name'],path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,Q=circuit.num_qubits,static_Toffolis=statistics.num_toffoli_like))
        if cut['phase_zero']:
            text=io.StringIO();circuit.to_file(text,format='kmx');native_text=text.getvalue()
            text_path=output/f'{name}_{cut["name"]}.kmx';text_path.write_text(native_text)
            proof=prove_native_text(native_text);symbolic.append(dict(cut=cut['name'],**proof))
            print(json.dumps(dict(case=name,cut=cut['name'],symbolic_status=proof['status'],HMR_variables=proof['HMR_variables'],maximum_terms=proof['maximum_total_polynomial_terms'])),flush=True)
        for seed in (0,1,2,3):
            rng=np.random.default_rng(2026111200+seed);addresses=np.tile(np.arange(128,dtype=np.uint64),2)
            spec=rng.integers(0,1<<len(spectators),256,dtype=np.uint64)
            sim=km.Simulator(batch_size=256,counting_operations=True,seed=seed)
            sim.clear_for_shot();sim.write_across_shots(array(address),bits(addresses,7));sim.write_across_shots(array(spectators),bits(spec,len(spectators)));sim.do(circuit)
            assert np.array_equal(read(sim,address),addresses),(name,cut['name'],seed,'address')
            assert np.array_equal(read(sim,spectators),spec),(name,cut['name'],seed,'spectators')
            if cut['A']:
                assert np.array_equal(read(sim,cut['A']),modelA[addresses]),(name,cut['name'],seed,'A')
                assert np.array_equal(read(sim,cut['H']),modelH[addresses]),(name,cut['name'],seed,'H')
            if cut['extras']:
                assert np.array_equal(read(sim,cut['extras']),spec&31),(name,cut['name'],seed,'extra spectators')
            keep=set(address+spectators+cut['A']+cut['H']+cut['extras'])
            scratch=[km.q(i) for i in range(circuit.num_qubits) if km.q(i) not in keep]
            if scratch:assert not sim.read_across_shots(array(scratch)).any(),(name,cut['name'],seed,'scratch')
            if cut['phase_zero']:
                assert all(sim.read_shot_phase(i)%2==0 for i in range(256)),(name,cut['name'],seed,'phase')
            measured=sim.operation_statistics().num_toffoli_like/256
            assert measured==cut['Toffolis'],(name,cut['name'],seed,'measured gates',measured)
            record=dict(cut=cut['name'],seed=seed,shots=256,all128_addresses=True,spectator_bits=len(spectators)+len(cut['extras']),
                        output_values='PASS' if cut['A'] else 'all outputs erased',scratch='ZERO',phase='EXACT_ZERO_MOD2' if cut['phase_zero'] else 'explicitly deferred',
                        native_measured_Toffolis=measured,status='PASS')
            records.append(record);print(json.dumps(dict(case=name,**record)),flush=True)
    result=dict(status='PASS_NATIVE_TABLE_COMPONENT_NOT_OFFICIAL',case=name,model_sha256=MODEL_SHA,native_Q=49,
                fixture={k:v for k,v in fixture.items() if k not in ('builder','address','spectators','cuts')},circuits=circuits,checks=records,native_text_symbolic_proofs=symbolic,
                seconds=time.monotonic()-began,scope='Native simulator data/spectator/scratch/phase checks on every address for four seeds, plus exact symbolic proof of freshly emitted native KMX text for every spectator input and every HMR transcript. This is not a complete invsqrt official-verifier qualification.')
    atomic_json(output/f'{name}_proof.json',result);return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=('first','second','deferred','all'),default='all');args=ap.parse_args()
    gate=verify_gate_sources();output=HERE/'table_proofs';output.mkdir(exist_ok=True)
    names=('first','second','deferred') if args.case=='all' else (args.case,);results=[];began=time.monotonic()
    for name in names:
        print(json.dumps(dict(stage='building',case=name)),flush=True)
        fixture=build_deferred() if name=='deferred' else build_single(name)
        results.append(prove_case(name,fixture,output))
    result=dict(status='PASS_NATIVE_TABLE_COMPONENTS_NOT_OFFICIAL',cases=[r['case'] for r in results],
                model_sha256=MODEL_SHA,gate_status=gate.get('status'),source_pins=PINS,
                first_loader_Toffolis=60,second_loader_Toffolis=73,final_cleanup_Toffolis=9,
                all_native_Q=49,total_native_shots=sum(c['shots'] for r in results for c in r['checks']),
                elapsed_seconds=time.monotonic()-began,official_verifier=False,no_submission=True)
    atomic_json(output/f'aggregate_{args.case}.json',result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
