#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Emit the paper-authorized arithmetic composition around frozen phase07."""
from pathlib import Path
import argparse, hashlib, json, time
import arithmetic_variant as variant

from branch_prover import Program, generated_text
from fourier_resource_expectation import exact_expectation


def build():
    gate = variant.accepted_gate()
    components = variant.install()
    old = variant.old
    common = old.common
    base = old.load_baseline('generate')
    tables = old.local_module('tables07')
    lifecycle = components['lifecycle']
    decoder = old.inherited_module('decoder06')
    phase = old.local_module('phase07')
    builder = common.km.CircuitBuilder()
    builder.set_max_qubits(gate['Q'])
    original = list(builder.alloc_qubits(22))
    flags = list(builder.alloc_qubits(4))
    cuts, owner_trace = [], []

    def mark(label, current, owners):
        cuts.append(base.snapshot(current, label, owners))

    lifecycle.CUT_HOOK = mark
    components['normalization'].forward(builder, original, flags)
    mark('normalized', builder, dict(n=original, flags=flags))
    root = components['root'].forward(builder, original)
    v, h = list(root['root']), list(root['residual'])
    mark('consumed_root', builder, dict(v=v, h=h, flags=flags))
    v, h = lifecycle.emit_body(builder, v, h, flags, tables, old.divider,
                               decoder.decode_root, trace=owner_trace)
    assert len(set(v + h + flags)) == 26 and builder.num_allocated_qubits == 26
    mark('body_restored', builder, dict(v=v, h=h, flags=flags))
    norm = h + v
    components['root'].inverse(builder, norm)
    mark('root_restored', builder, dict(n=norm, flags=flags))
    components['normalization'].inverse(builder, norm, flags)
    builder.free(common.array(flags))
    mark('logical_input_restored', builder, dict(x=norm))
    layout = base.restore_input_layout(builder, norm, original, gate['Q'])
    circuit = common.with_registers(builder.finish_circuit(), dict(x=original))
    text = generated_text(circuit)
    program, resources = Program(text), exact_expectation(text)
    wanted = dict(toffoli_like=gate['expected_Toffolis'], T=gate['T'],
                  generic_rotations=gate['R'])
    assert circuit.num_qubits == gate['Q'] == 48
    assert resources['mean_numeric'] == wanted, (resources['mean_numeric'], wanted)
    assert program.modulus == 1 << 50
    assert list(circuit.register_data) == ['x']
    assert list(circuit.register_data['x']) == original
    assert all(cut['peak_so_far'] <= gate['Q'] for cut in cuts)
    assert len(phase.LAST_ANGLE_RECORDS) == 34 and len(phase.ROUTE_TRACE) == 2
    variant.verify_sources()
    report = dict(status='EMITTED_NATIVE_ARITHMETIC_COMPOSITION_NOT_YET_QUALIFIED',
        candidate=gate['candidate'], Q=gate['Q'], exact_native_expectation=resources,
        paper_rotation_charge=gate['rotation_charge'], paper_cost=gate['expected_cost'],
        components_expected_Toffolis=gate['components_expected_Toffolis'],
        cuts=cuts, owner_trace=owner_trace, final_Clifford_layout_swaps=layout,
        route_trace=phase.ROUTE_TRACE, phase_angle_records=phase.LAST_ANGLE_RECORDS,
        phase_trace=phase.LAST_PHASE_TRACE, phase_basis='ring26_global_zero33',
        phase_modulus=1 << 50, model_sha256=common.MODEL_SHA,
        accuracy_receipt_sha256=gate['accuracy_receipt_sha256'],
        quantized_exact_minimum_margin_units64=124370688,
        independent_phase_units50_sha256=gate['independent_phase_units50_sha256'],
        paper_gate_sha256=variant.sha(variant.HERE / 'COMPLETE_GATE.json'),
        parent_authorization_sha256=variant.sha(variant.HERE / 'PARENT_ACCEPTED.json'),
        source_ready_sha256=variant.sha(variant.HERE / 'SOURCE_READY.json'),
        input_manifest_sha256=variant.sha(variant.HERE / 'INPUTS.json'),
        actual_HMR_variables=program.measurements,
        protected_phase_tables_angles_oracle_unchanged=True,
        all_prior_candidates_unchanged=True, official_verifier=False, no_submission=True)
    return circuit, text, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=variant.HERE / 'candidate10.kmb')
    args = ap.parse_args()
    assert not args.output.exists(), 'Preserve an already emitted candidate.'
    began = time.monotonic()
    circuit, text, report = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    circuit.to_file(str(args.output), format='kmb')
    args.output.with_suffix('.kmx').write_text(text)
    report.update(kmb_sha256=variant.sha(args.output),
        native_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        bytes=args.output.stat().st_size, emission_seconds=time.monotonic() - began,
        native_sources={p.name: variant.sha(p) for p in sorted(variant.HERE.glob('*.py'))})
    args.output.with_suffix('.build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'candidate', 'Q',
        'exact_native_expectation', 'paper_cost', 'kmb_sha256', 'emission_seconds')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
