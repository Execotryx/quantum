#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Emit candidate05 and enforce the exact route-only structural contract."""
from pathlib import Path
import argparse,hashlib,json,time
import variant
from branch_prover import Program,generated_text


def structural_contract(circuit):
    old_circuit=variant.common.km.Circuit.from_file(str(variant.PREVIOUS/'candidate04.kmb'))
    old=Program(generated_text(old_circuit));new=Program(generated_text(circuit))
    assert old.modulus==new.modulus==1<<50
    assert old.registers==new.registers and old.wires==new.wires and old.measurements==new.measurements
    assert len(old.operations)==len(new.operations)+2
    traces=variant.ROUTE_TRACE
    assert len(traces)==2 and [r['inverse'] for r in traces]==[False,True]
    old_cursor=new_cursor=0;old_extra=0;blocks=[]
    for row in traces:
        new_start,new_stop=row['start'],row['stop'];old_start=new_start+old_extra;old_stop=new_stop+old_extra+1
        assert old.operations[old_cursor:old_start]==new.operations[new_cursor:new_start],('Outside route prefix changed',new_start)
        a=old.operations[old_start:old_stop];b=new.operations[new_start:new_stop]
        assert [o for o in a if o.kind!='CSWAP']==[o for o in b if o.kind!='CSWAP'],('Route affine/control instructions changed',row['inverse'])
        old_swaps=[o for o in a if o.kind=='CSWAP'];new_swaps=[o for o in b if o.kind=='CSWAP']
        assert [list(o.arguments) for o in old_swaps]==row['old_cswap_arguments']
        assert [list(o.arguments) for o in new_swaps]==row['new_cswap_arguments']
        assert all(o.condition is None and o.half_turns is None and o.event is None for o in old_swaps+new_swaps)
        assert len(old_swaps)==65 and len(new_swaps)==64 and len(a)==len(b)+1
        blocks.append(dict(inverse=row['inverse'],old_instruction_interval=[old_start,old_stop],
            new_instruction_interval=[new_start,new_stop],old_CSWAP=65,new_CSWAP=64,omissions=row['omissions']))
        old_cursor=old_stop;new_cursor=new_stop;old_extra+=1
    assert old.operations[old_cursor:]==new.operations[new_cursor:],'Outside route suffix changed'
    assert [o for o in old.operations if o.kind=='Z_POW']==[o for o in new.operations if o.kind=='Z_POW']
    return dict(status='EXACT_NATIVE_ROUTE_ONLY_STRUCTURAL_CONTRACT_PASS',phase_modulus=1<<50,
        old_native_operations=len(old.operations),new_native_operations=len(new.operations),
        old_route_CSWAP=130,new_route_CSWAP=128,route_blocks=blocks,
        all_nonroute_operations_identical=True,all_route_nonCSWAP_operations_identical=True,
        every_angle_and_target_identical=True,all_HMR_events_and_conditions_identical=True,
        all_registers_and_physical_owners_identical=True,phase_slots_unchanged=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=variant.HERE/'candidate05.kmb');args=ap.parse_args()
    began=time.monotonic();variant.install();gate=variant.variant_gate();variant.ROUTE_TRACE.clear()
    generator=variant.load_baseline('generate');generator.verify_gate_sources=variant.variant_gate
    circuit,text,report=generator.build();contract=structural_contract(circuit)
    assert report['exact_native_expectation']['mean_numeric']==dict(toffoli_like=1560.5,T=4.0,generic_rotations=34.0)
    assert report['Q']==49 and report['paper_cost']==gate['primary']['paper_cost']
    args.output.parent.mkdir(parents=True,exist_ok=True);circuit.to_file(str(args.output),format='kmb');args.output.with_suffix('.kmx').write_text(text)
    quantized,quant_sha=variant.checked_quantized()
    report.update(candidate='candidate05_constant_endpoint_route',kmb_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
        bytes=args.output.stat().st_size,variant_gate_sha256=hashlib.sha256((variant.NARROW/'PAPER_GATE_RECEIPT_016_VARIANT.json').read_bytes()).hexdigest(),
        variant_input_manifest_sha256=hashlib.sha256((variant.HERE/'INPUTS.json').read_bytes()).hexdigest(),
        quantize50_sha256=quant_sha,quantized_exact_minimum_margin_units64=124372027,phase_modulus=1<<50,
        route_only_structural_contract=contract,route_trace=variant.ROUTE_TRACE,
        phase_proxy_records=variant.previous.LAST_PROXY_RECORDS,preserved_candidates=['candidate01','candidate02','candidate03','candidate04'],
        baseline_sources_unchanged=True,angles_identical_to_candidate04=True,
        arithmetic_change='Only the common reflection-centre offset and the two constant-endpoint swap omissions.',
        native_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(variant.HERE.glob('*.py'))},
        emission_seconds=time.monotonic()-began)
    assert len(report['phase_proxy_records'])==34
    args.output.with_suffix('.build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
