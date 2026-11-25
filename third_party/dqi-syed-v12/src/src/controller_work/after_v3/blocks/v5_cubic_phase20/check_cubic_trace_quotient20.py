#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Exhaust all4096 GF64 source/numerator pairs; actual phase and reset checks."""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib
import json
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from accepted_runtime import load,recheck,digest,loaded_sources

RETAINED = 879
SEEDS = (63191,64191,65191)
PROBE_T = 3


def multiply(a,b):
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        if a & 64:
            a ^= 0x43
        b >>= 1
    return result


def inverse(a):
    answer,power = 1,62
    while power:
        if power & 1:
            answer = multiply(answer,a)
        a = multiply(a,a)
        power >>= 1
    return answer


def trace(a):
    answer = 0
    for _ in range(6):
        answer ^= a
        a = multiply(a,a)
    assert answer in (0,1)
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--per-source',type=int,default=64)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    assert __debug__ and sys.version_info[:2] == (3,13) and 1 <= args.per_source <= 64
    args.output.mkdir(parents=True,exist_ok=True)
    report_path = args.output/'report.json'
    assert not report_path.exists()
    runtime = load()
    km,np = importlib.import_module('kickmix'),importlib.import_module('numpy')
    candidate = importlib.import_module('cubic_trace_quotient20')
    bits = importlib.import_module('quantum_reciprocal').bit_matrix
    pins = {str(Path(module.__file__).resolve()):digest(module.__file__)
            for module in (candidate,candidate.Cubic)}
    started = time.monotonic()
    d = np.repeat(np.arange(args.per_source,dtype=np.int64),64)
    n = np.tile(np.arange(64,dtype=np.int64),args.per_source)
    count = len(d)
    rng = np.random.default_rng(202611112002)
    dirty = rng.integers(0,2,(RETAINED-12,count),dtype=np.int8).astype(bool)
    masks = rng.integers(0,64,count,dtype=np.int64)
    arrays = dict(denominator=bits(d,6),numerator=bits(n,6),mask=bits(masks,6),dirty=dirty)
    desired = np.array([trace(multiply(int(x),inverse(int(y)))) for x,y in zip(n,d)],dtype=bool)
    probe = ((d&1)!=0)&((n&2)!=0)&dirty[0]
    probe ^= ((d&4)!=0)&((n&8)!=0)&dirty[1]
    probe ^= ((d&16)!=0)&((n&32)!=0)&dirty[2]
    probe ^= np.array([(int(x)&int(y)).bit_count()&1 for x,y in zip(masks,d)],dtype=bool)
    report = dict(status='IN_PROGRESS_CUBIC20_NATIVE_PHASE',cases=count,
        all_64_numerators=True,denominators=args.per_source,
        exhaustive_all_field_pairs=args.per_source==64,seeds=list(SEEDS),rows=[],
        original_sources=pins,full_preimage_or_official_checked=False)
    def save():
        temp=report_path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');temp.replace(report_path)
    save()
    def build(paired):
        b=km.CircuitBuilder();b.set_max_qubits(889)
        den=b.create_quantum_register(6,'denominator')
        num=b.create_quantum_register(6,'numerator')
        mask=b.create_classical_register(6,'mask')
        bystanders=b.create_quantum_register(RETAINED-12,'dirty')
        candidate.phase_trace_quotient_six(b,den,num)
        b.ccz(den[0],num[1],bystanders[0]);b.ccz(den[2],num[3],bystanders[1])
        b.ccz(den[4],num[5],bystanders[2]);b.cz(mask,den)
        if paired:
            candidate.phase_trace_quotient_six(b,den,num)
        assert b.num_allocated_qubits == RETAINED
        circuit=b.finish_circuit()
        assert circuit.num_qubits == 889
        assert circuit.operation_statistics().num_toffoli_like == (40 if paired else 20)+PROBE_T
        return circuit
    for paired in (False,True):
        label='pair' if paired else 'phase'
        paths=[args.output/f'{label}-{letter}.kmb' for letter in ('a','b')]
        circuit=build(paired);circuit.to_file(paths[0],format='kmb');first_sha=digest(paths[0])
        expected_phase=probe if paired else probe^desired
        runs=[]
        for seed in SEEDS:
            sim=km.Simulator(batch_size=count,seed=seed,counting_operations=True)
            sim.use_same_registers_as(circuit)
            for name,value in arrays.items():sim.write_across_shots(circuit.register_data[name],value)
            sim.do(circuit)
            errors={name:np.flatnonzero(np.any(sim.read_across_shots(circuit.register_data[name])!=value,axis=0)).tolist()
                    for name,value in arrays.items()}
            phase_errors=np.flatnonzero(sim.read_phase_flipped_across_shots()!=expected_phase).tolist()
            scratch=bool(sim.read_across_shots([km.q(i) for i in range(RETAINED,889)]).any())
            total=sim.operation_statistics().num_toffoli_like
            assert not any(errors.values()) and not phase_errors and not scratch
            assert total==count*((40 if paired else 20)+PROBE_T)
            runs.append(dict(seed=seed,value_error_case_ids=errors,phase_error_case_ids=phase_errors,
                             scratch_errors=scratch,total_T=total,measured_mean_T=total/count-PROBE_T))
            del sim;gc.collect()
        del circuit;gc.collect()
        second=build(paired);second.to_file(paths[1],format='kmb')
        assert digest(paths[1])==first_sha
        del second;gc.collect()
        report['rows'].append(dict(panel=label,static_T=40 if paired else 20,Q=889,
            retained_Q=RETAINED,helpers=10,two_identical_builds=True,circuit_sha256=first_sha,runs=runs));save()
        for path in paths:path.unlink()
    rejected=[]
    for kind in ('wrong_length','same_word','duplicate_wire','classical_numerator'):
        b=km.CircuitBuilder();den=b.create_quantum_register(6,'den');num=b.create_quantum_register(6,'num')
        if kind=='wrong_length':den=den[:5]
        elif kind=='same_word':num=den
        elif kind=='duplicate_wire':num=km.array([num[1],*num[1:]])
        else:num=b.create_classical_register(6,'classical')
        try:candidate.phase_trace_quotient_six(b,den,num)
        except (ValueError,TypeError):rejected.append(kind)
        else:raise AssertionError('Malformed contract accepted')
        assert b.num_allocated_qubits==12 and b.finish_circuit().operation_statistics().num_toffoli_like==0
    assert pins=={name:digest(name) for name in pins}
    report.update(status='PASS_NATIVE_CUBIC20_TRACE_QUOTIENT_COMPONENT',
        elapsed_seconds=time.monotonic()-started,rejected_contracts=rejected,
        accepted_source_preservation=recheck(runtime),loaded_sources=loaded_sources(),
        conditional_full_preimage_mean_saving='18*(1-2**-24)',whole_decoder_gain_banked=False)
    save();print(json.dumps(dict(status=report['status'],cases=count,elapsed_seconds=report['elapsed_seconds'])),flush=True)


if __name__=='__main__':
    main()
