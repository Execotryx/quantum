#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Emit the complete Q48 schedule only after its complete paper authorization."""
from pathlib import Path
from fractions import Fraction
import argparse
import hashlib
import json
import time
import variant

from branch_prover import Program, generated_text
from fourier_resource_expectation import exact_expectation


def build():
    variant.install()
    gate = variant.variant_gate()
    common = variant.common
    base = variant.load_baseline('generate')
    tables = variant.local_module('tables06')
    lifecycle = variant.local_module('lifecycle06')
    decoder = variant.local_module('decoder06')
    phase = variant.local_module('phase06')
    builder = common.km.CircuitBuilder()
    builder.set_max_qubits(48)
    original = list(builder.alloc_qubits(22))
    flags = list(builder.alloc_qubits(4))
    cuts = []
    owner_trace = []

    def mark(label, current_builder, owners):
        cuts.append(base.snapshot(current_builder, label, owners))

    assert hasattr(lifecycle, 'CUT_HOOK'), 'The Q48 lifecycle must expose explicit native resource cuts.'
    lifecycle.CUT_HOOK = mark
    variant.previous.ROUTE_TRACE.clear()
    base.normalization.forward(builder, original, flags)
    mark('normalized', builder, dict(n=original, flags=flags))
    root = base.consuming_root.forward(builder, original)
    v, h = list(root['root']), list(root['residual'])
    mark('consumed_root', builder, dict(v=v, h=h, flags=flags))
    v, h = lifecycle.emit_body(builder, v, h, flags, tables, variant.divider, decoder.decode_root, trace=owner_trace)
    assert len(set(v + h + flags)) == 26 and builder.num_allocated_qubits == 26
    mark('body_restored', builder, dict(v=v, h=h, flags=flags))
    norm = h + v
    base.consuming_root.inverse(builder, norm)
    mark('root_restored', builder, dict(n=norm, flags=flags))
    base.normalization.inverse(builder, norm, flags)
    builder.free(common.array(flags))
    mark('logical_input_restored', builder, dict(x=norm))
    layout = base.restore_input_layout(builder, norm, original, 48)
    circuit = common.with_registers(builder.finish_circuit(), dict(x=original))
    text = generated_text(circuit)
    program = Program(text)
    resources = exact_expectation(text)
    actual = resources['mean_numeric']
    assert circuit.num_qubits == 48
    assert actual == dict(toffoli_like=1591.0, T=4.0, generic_rotations=34.0), ('complete_resource_gate', actual)
    assert program.modulus == 1 << 50
    assert list(circuit.register_data) == ['x'] and list(circuit.register_data['x']) == original
    assert all(cut['peak_so_far'] <= 48 for cut in cuts)
    assert len(phase.LAST_PROXY_RECORDS) == 34
    assert [row['new_half_turns'] for row in phase.LAST_PROXY_RECORDS] == [
        str(Fraction(2 * n, 1 << 50)) for n in variant.NEW_TURN_UNITS50]
    assert len(variant.previous.ROUTE_TRACE) == 2
    assert all(len(row['new_cswap_arguments']) == 64 for row in variant.previous.ROUTE_TRACE)
    report = dict(status='EMITTED_NATIVE_CANDIDATE_NOT_YET_PROVED_OR_OFFICIALLY_VERIFIED',
                  candidate='candidate06_complete_Q48', Q=48,
                  exact_native_expectation=resources, paper_rotation_charge=gate['rotation_charge'],
                  paper_cost=gate['paper_cost'], components_expected_Toffolis=gate['complete_components'],
                  cuts=cuts, owner_trace=owner_trace, final_Clifford_layout_swaps=layout,
                  route_trace=variant.previous.ROUTE_TRACE,
                  phase_proxy_records=phase.LAST_PROXY_RECORDS,
                  compact_phase_trace=phase.LAST_PHASE_TRACE,
                  phase_modulus=1 << 50, model_sha256=common.MODEL_SHA,
                  quantize50_sha256=gate['quantize50_sha256'],
                  quantized_exact_minimum_margin_units64=124372027,
                  paper_gate_sha256=variant.PAPER_SHA, parent_authorization_sha256=variant.GATE_SHA,
                  all_prior_candidates_unchanged=True, official_verifier=False, no_submission=True)
    return circuit, text, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=variant.HERE / 'candidate06.kmb')
    args = parser.parse_args()
    started = time.monotonic()
    circuit, text, report = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    circuit.to_file(str(args.output), format='kmb')
    args.output.with_suffix('.kmx').write_text(text)
    report.update(kmb_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  bytes=args.output.stat().st_size, emission_seconds=time.monotonic() - started,
                  native_sources={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(variant.HERE.glob('*.py'))})
    args.output.with_suffix('.build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'candidate', 'Q', 'exact_native_expectation',
                    'paper_cost', 'kmb_sha256', 'emission_seconds')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
