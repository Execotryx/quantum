#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Fresh candidate05 native proofs against the unchanged pinned50-unit oracle."""
from pathlib import Path
import argparse,hashlib,json,resource,time
import variant


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('selftest','sample','text'),required=True)
    ap.add_argument('--circuit',type=Path,default=variant.HERE/'candidate05.kmb')
    ap.add_argument('--shots',type=int,default=8192);ap.add_argument('--seeds',default='0,1,2,3')
    ap.add_argument('--first',type=int,default=1);ap.add_argument('--last',type=int,default=3133453)
    ap.add_argument('--chunk',type=int,default=65536);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();began=time.monotonic();variant.variant_gate();quantized,quant_sha=variant.checked_quantized()
    proof=variant.proof50_module();assert proof.MODULUS==1<<50
    tests=proof.selftest50()
    if args.mode=='selftest':result=tests
    else:
        raw=args.circuit.read_bytes();digest=hashlib.sha256(raw).hexdigest();circuit=variant.common.km.Circuit.from_file(str(args.circuit))
        assert circuit.num_qubits==49 and list(circuit.register_data)==['x'] and len(circuit.register_data['x'])==22
        build=json.loads(args.circuit.with_suffix('.build.json').read_text())
        assert build['kmb_sha256']==digest and build['quantize50_sha256']==quant_sha
        assert build['route_only_structural_contract']['status']=='EXACT_NATIVE_ROUTE_ONLY_STRUCTURAL_CONTRACT_PASS'
        assert build['exact_native_expectation']['mean_numeric']==dict(toffoli_like=1560.5,T=4.0,generic_rotations=34.0)
        assert proof.Program(proof.generated_text(circuit)).modulus==1<<50
        if args.mode=='sample':
            result=proof.native_sample(circuit,args.shots,list(map(int,args.seeds.split(','))))
            result['status']='PASS_NATIVE_SAMPLED_CANDIDATE05_NOT_OFFICIAL'
        else:result=proof.exhaustive_text(circuit,args.first,args.last,args.chunk,args.output,quantized)
        result.update(circuit_sha256=digest,Q=49,exact50_unit_selftest=tests)
    result.update(candidate='candidate05_constant_endpoint_route',phase_modulus=1<<50,
        arithmetic_model_sha256=variant.common.MODEL_SHA,quantize50_sha256=quant_sha,
        quantized_exact_minimum_margin_units64=124372027,expected_native_Toffolis=1560.5,
        unchanged_candidate04_angles=True,unchanged_original_tolerance=True,
        pinned_candidate04_oracle_sha256=hashlib.sha256((variant.PREVIOUS/'oracle50.py').read_bytes()).hexdigest(),
        pinned_candidate04_proof_functions_sha256=hashlib.sha256((variant.PREVIOUS/'prove50.py').read_bytes()).hexdigest(),
        official_verifier=False,no_submission=True,elapsed_seconds=time.monotonic()-began,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    proof.atomic(args.output,result);print(json.dumps({k:v for k,v in result.items() if k!='chunks'},indent=2),flush=True)


if __name__=='__main__':main()
