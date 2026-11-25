#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Emit only after the exact quantized scan, then prove an angle-only diff."""
from pathlib import Path
from fractions import Fraction
import argparse,hashlib,json,time
import variant
from branch_prover import Program,generated_text


def structural_diff(circuit):
    old=variant.common.km.Circuit.from_file(str(variant.HERE.parent/'candidate03/candidate03.kmb'))
    previous=Program(generated_text(old));current=Program(generated_text(circuit))
    assert previous.modulus==1<<37 and current.modulus==1<<50
    assert previous.registers==current.registers and previous.wires==current.wires
    assert previous.measurements==current.measurements
    assert len(previous.operations)==len(current.operations)
    changes=[]
    for index,(a,b) in enumerate(zip(previous.operations,current.operations)):
        assert(a.kind,a.arguments,a.condition,a.event)==(b.kind,b.arguments,b.condition,b.event),('Non-angle native change',index,a,b)
        if a.half_turns==b.half_turns:continue
        assert a.kind=='Z_POW'
        site=len(changes);assert site<34
        # Kickmix serializes Z_POW half turns canonically modulo2, including
        # the negative j0 threshold angle. The source proxy checks the signed
        # argument; the parsed native diff checks the identical modular value.
        assert a.half_turns==Fraction(2*variant.COEFFICIENTS37[site],1<<37)%2
        assert b.half_turns==Fraction(2*variant.NEW_TURN_UNITS50[site],1<<50)%2
        assert variant.angle_class(a.half_turns)==variant.angle_class(b.half_turns)=='generic'
        changes.append(dict(instruction=index,site=variant.SITES[site],target=list(a.arguments),old_half_turns=str(a.half_turns),new_half_turns=str(b.half_turns)))
    assert len(changes)==34
    assert len(variant.LAST_PROXY_RECORDS)==34
    return dict(status='EXACT_PARSED_NATIVE_34_ANGLE_ONLY_DIFF',changes=changes,native_operations=len(current.operations),
                HMR_variables=current.measurements,all_registers_unchanged=True,all_operands_and_conditions_unchanged=True,
                all_other_phases_unchanged=True,old_modulus=previous.modulus,new_modulus=current.modulus)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=variant.HERE/'candidate04.kmb');args=ap.parse_args()
    began=time.monotonic();variant.install();gate=variant.variant_gate()
    generator=variant.load_baseline('generate');generator.verify_gate_sources=variant.variant_gate
    circuit,text,report=generator.build();diff=structural_diff(circuit)
    args.output.parent.mkdir(parents=True,exist_ok=True);circuit.to_file(str(args.output),format='kmb')
    args.output.with_suffix('.kmx').write_text(text)
    quantized,quant_sha=variant.checked_quantized()
    report.update(candidate='candidate04_quantized_angle_refit',kmb_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
        bytes=args.output.stat().st_size,variant_gate_sha256=hashlib.sha256((variant.NARROW/'PAPER_GATE_RECEIPT_014_VARIANT.json').read_bytes()).hexdigest(),
        variant_input_manifest_sha256=hashlib.sha256((variant.HERE/'INPUTS.json').read_bytes()).hexdigest(),
        quantize50_sha256=quant_sha,quantized_exact_minimum_margin_units64=quantized['exact_statistics']['quantized50']['minimum_margin_units'],
        conservative_minimum_margin_units64=124286782,phase_modulus=1<<50,structural_angle_only_diff=diff,
        phase_proxy_records=variant.LAST_PROXY_RECORDS,preserved_candidates=['candidate01','candidate02','candidate03'],
        baseline_sources_unchanged=True,arithmetic_change=None,
        phase_change='Only the34 generic phase angles, rounded exactly to2^-50 turns.',
        native_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(variant.HERE.glob('*.py'))},
        emission_seconds=time.monotonic()-began)
    assert report['exact_native_expectation']['mean_numeric']==dict(toffoli_like=1562.5,T=4.0,generic_rotations=34.0)
    assert report['Q']==49 and report['paper_cost']==gate['primary']['paper_cost']
    args.output.with_suffix('.build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
