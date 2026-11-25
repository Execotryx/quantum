#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Original exact50 checker and oracle, with new arithmetic source bindings.

All original proof functions, self-tests and checks are called unchanged.
The composition's arithmetic count is checked against its own frozen gate.
"""
from pathlib import Path
import argparse, importlib.util, json, resource, sys, time
import arithmetic_variant as variant
from branch_prover import Program, generated_text


def original_proof():
    path = variant.NARROW / 'native/candidate07/prove50.py'
    assert variant.sha(path) == 'd079cefb01fa88581cf279e99590ad74610551861658f5fef65ff9071650216e'
    name = 'candidate10_immutable_candidate07_proof50'
    if name not in sys.modules:
        previous_variant = sys.modules.get('variant')
        sys.modules['variant'] = variant.old
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        finally:
            if previous_variant is None:
                sys.modules.pop('variant', None)
            else:
                sys.modules['variant'] = previous_variant
    proof = sys.modules[name]
    assert proof.variant is variant.old
    assert proof.MODULUS == 1 << 50 and proof.MAX_X == 3133452
    return proof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('selftest', 'sample', 'text'), required=True)
    ap.add_argument('--circuit', type=Path, default=variant.HERE / 'candidate10.kmb')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    assert not args.output.exists(), 'Preserve completed native proof evidence.'
    began = time.monotonic()
    gate = variant.accepted_gate()
    old_proof = original_proof()
    fit, fit_sha = variant.old.accuracy_receipt()
    assert fit_sha == gate['accuracy_receipt_sha256']
    tests = old_proof.selftest50()
    assert tests['positive_cases'] == 5 and tests['negative_cases'] == 9
    if args.mode == 'selftest':
        result = tests
    else:
        digest = variant.sha(args.circuit)
        circuit = variant.old.common.km.Circuit.from_file(str(args.circuit))
        build = json.loads(args.circuit.with_suffix('.build.json').read_text())
        assert circuit.num_qubits == gate['Q'] == 48
        assert list(circuit.register_data) == ['x'] and len(circuit.register_data['x']) == 22
        assert build['kmb_sha256'] == digest
        assert build['paper_gate_sha256'] == variant.sha(variant.HERE / 'COMPLETE_GATE.json')
        assert build['parent_authorization_sha256'] == variant.sha(variant.HERE / 'PARENT_ACCEPTED.json')
        assert build['source_ready_sha256'] == variant.sha(variant.HERE / 'SOURCE_READY.json')
        assert build['input_manifest_sha256'] == variant.sha(variant.HERE / 'INPUTS.json')
        assert build['accuracy_receipt_sha256'] == fit_sha
        assert build['phase_basis'] == 'ring26_global_zero33'
        assert build['phase_modulus'] == 1 << 50
        assert build['independent_phase_units50_sha256'] == fit['exact_screen']['phase50_sha256']
        assert build['exact_native_expectation']['mean_numeric'] == dict(
            toffoli_like=gate['expected_Toffolis'], T=gate['T'], generic_rotations=gate['R'])
        assert Program(generated_text(circuit)).modulus == 1 << 50
        if args.mode == 'sample':
            result = old_proof.native_sample(circuit, 8192, [0, 1, 2, 3])
            result['status'] = 'PASS_NATIVE_SAMPLED_CANDIDATE10_NOT_OFFICIAL'
        else:
            result = old_proof.exhaustive_text(circuit, 1, old_proof.MAX_X + 1,
                                               65536, args.output, fit)
        result.update(circuit_sha256=digest, Q=gate['Q'], exact50_unit_selftest=tests)
    variant.verify_sources()
    result.update(candidate=gate['candidate'], phase_basis='ring26_global_zero33',
        phase_modulus=1 << 50, arithmetic_model_sha256=variant.old.common.MODEL_SHA,
        accuracy_receipt_sha256=fit_sha,
        accuracy_receipt_path='research/ring26_phase/frozen/global_zero33.json',
        quantized_exact_minimum_margin_units64=124370688,
        independent_phase_units50_sha256=gate['independent_phase_units50_sha256'],
        expected_native_Toffolis=gate['expected_Toffolis'], expected_T=gate['T'], expected_R=gate['R'],
        unchanged_original_tolerance=True, protected_phase_tables_angles_oracle_unchanged=True,
        original_candidate07_proof_source_sha256=variant.sha(variant.NARROW / 'native/candidate07/prove50.py'),
        original_oracle_source_sha256=variant.sha(variant.NARROW / 'native/candidate07/oracle50.py'),
        local_proof_source_sha256=variant.sha(Path(__file__)),
        phase_source_sha256=variant.sha(variant.NARROW / 'native/candidate07/phase07.py'),
        parent_authorization_sha256=variant.sha(variant.HERE / 'PARENT_ACCEPTED.json'),
        paper_gate_sha256=variant.sha(variant.HERE / 'COMPLETE_GATE.json'),
        source_ready_sha256=variant.sha(variant.HERE / 'SOURCE_READY.json'),
        input_manifest_sha256=variant.sha(variant.HERE / 'INPUTS.json'),
        official_verifier=False, no_submission=True, elapsed_seconds=time.monotonic() - began,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    old_proof.atomic(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'chunks'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
