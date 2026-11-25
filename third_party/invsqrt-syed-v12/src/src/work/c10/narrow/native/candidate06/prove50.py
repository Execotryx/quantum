#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Fresh Q48 native proofs against the immutable independent integer50 oracle."""
from pathlib import Path
import argparse
import hashlib
import json
import resource
import time
import variant


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('selftest', 'sample', 'text'), required=True)
    parser.add_argument('--circuit', type=Path, default=variant.HERE / 'candidate06.kmb')
    parser.add_argument('--shots', type=int, default=8192)
    parser.add_argument('--seeds', default='0,1,2,3')
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--last', type=int, default=3133453)
    parser.add_argument('--chunk', type=int, default=65536)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    gate = variant.variant_gate()
    quantized, quant_sha = variant.checked_quantized()
    proof = variant.proof50_module()
    assert proof.MODULUS == 1 << 50
    tests = proof.selftest50()
    if args.mode == 'selftest':
        result = tests
    else:
        digest = hashlib.sha256(args.circuit.read_bytes()).hexdigest()
        circuit = variant.common.km.Circuit.from_file(str(args.circuit))
        assert circuit.num_qubits == 48 and list(circuit.register_data) == ['x']
        assert len(circuit.register_data['x']) == 22
        build = json.loads(args.circuit.with_suffix('.build.json').read_text())
        assert build['kmb_sha256'] == digest and build['quantize50_sha256'] == quant_sha
        assert build['parent_authorization_sha256'] == variant.GATE_SHA
        assert build['paper_gate_sha256'] == variant.PAPER_SHA
        assert build['exact_native_expectation']['mean_numeric'] == dict(toffoli_like=1591.0, T=4.0, generic_rotations=34.0)
        assert proof.Program(proof.generated_text(circuit)).modulus == 1 << 50
        if args.mode == 'sample':
            result = proof.native_sample(circuit, args.shots, list(map(int, args.seeds.split(','))))
            result['status'] = 'PASS_NATIVE_SAMPLED_CANDIDATE06_NOT_OFFICIAL'
        else:
            result = proof.exhaustive_text(circuit, args.first, args.last, args.chunk, args.output, quantized)
        result.update(circuit_sha256=digest, Q=48, exact50_unit_selftest=tests)
    result.update(candidate='candidate06_complete_Q48', phase_modulus=1 << 50,
                  arithmetic_model_sha256=variant.common.MODEL_SHA,
                  quantize50_sha256=quant_sha, quantized_exact_minimum_margin_units64=124372027,
                  expected_native_Toffolis=1591.0, unchanged_candidate04_angles=True,
                  unchanged_original_tolerance=True,
                  pinned_candidate04_oracle_sha256=hashlib.sha256((variant.HERE.parent / 'candidate04/oracle50.py').read_bytes()).hexdigest(),
                  pinned_candidate04_proof_functions_sha256=hashlib.sha256((variant.HERE.parent / 'candidate04/prove50.py').read_bytes()).hexdigest(),
                  parent_authorization_sha256=variant.GATE_SHA,
                  official_verifier=False, no_submission=True,
                  elapsed_seconds=time.monotonic() - began,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    proof.atomic(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'chunks'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
