#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded build of a separate fixed Q889 integration candidate."""
from pathlib import Path
import argparse
import gc
import json
import time
import integration_paths  # noqa: F401
from source_binding import atomic_json, digest, verify_accepted_sources, write_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--log-directory', type=Path, required=True)
    parser.add_argument('--engineering-scan-positions', type=int, default=4095)
    parser.add_argument('--first-two-charts', action='store_true')
    parser.add_argument('--nested-norm', action='store_true')
    parser.add_argument('--finish-seam', action='store_true')
    args = parser.parse_args()
    assert 0 < args.engineering_scan_positions <= 4095
    args.output = args.output.resolve()
    args.log_directory = args.log_directory.resolve()
    assert not args.output.exists(), 'Refuse to overwrite any circuit artifact'
    assert not (args.log_directory/'build.json').exists(), 'Use a new build-log directory'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.log_directory.mkdir(parents=True, exist_ok=True)
    before = verify_accepted_sources()
    import kickmix as km
    import integrated_pipeline as Pipeline
    from event_ledger import Events
    options = Pipeline.Options(args.first_two_charts, args.nested_norm, args.finish_seam)
    Pipeline.configure(options)
    events = Events()
    events.install(Pipeline)
    started = time.monotonic()
    builder = km.CircuitBuilder()
    builder.set_max_qubits(889)
    syndromes = [builder.create_quantum_register(12, f'S{i}') for i in range(70)]
    masks = [builder.create_classical_register(12, f'E{i}') for i in range(4095)]
    stages = []

    def stage(message):
        row = dict(stage=message, allocated_Q=builder.num_allocated_qubits,
                   elapsed_seconds=time.monotonic()-started)
        stages.append(row)
        atomic_json(args.log_directory/'build-status.json',
                    dict(status='BUILDING_UNVERIFIED_NEW_CANDIDATE', last=row,
                         completed_stages=stages, options=Pipeline.runtime_bindings()))
        print(json.dumps(row), flush=True)

    contract = Pipeline.emit(builder, syndromes, masks, j_min=15,
                             scan_positions=args.engineering_scan_positions, stage=stage)
    assert builder.num_allocated_qubits == 840
    circuit = builder.finish_circuit()
    del builder
    gc.collect()
    static_T = circuit.operation_statistics().num_toffoli_like
    expected = Pipeline.source_ledger(contract['scan']['static_T'])
    assert static_T == expected['total_static_T'], (static_T, expected)
    assert circuit.num_qubits == 889, circuit.num_qubits
    assert dict(circuit.operation_statistics()).get('Z_POW', 0) == 0
    event_report = events.snapshot(static_T, contract['scan']['point_tests'])
    instructions, bits = len(circuit), circuit.num_bits
    temporary = args.output.with_suffix(args.output.suffix+'.tmp')
    assert not temporary.exists()
    circuit.to_file(temporary, format='kmb')
    del circuit
    gc.collect()
    temporary.replace(args.output)
    after = verify_accepted_sources()
    inventory = write_inventory(args.log_directory/'source-inventory.json', Pipeline, before, after)
    report = dict(status='BUILT_UNVERIFIED_POST_C5_FIXED_CANDIDATE',
                  circuit=str(args.output), sha256=digest(args.output),
                  bytes=args.output.stat().st_size, Q=889, static_T=static_T,
                  instructions=instructions, classical_bits=bits,
                  measured_mean_T=None, uniform_mask_source_expectation=event_report,
                  nominal_cost=None, official_cost=None,
                  full_DQI_scan=args.engineering_scan_positions == 4095,
                  contract=contract, source_inventory=inventory,
                  elapsed_seconds=time.monotonic()-started, stages=stages,
                  limitations=['A build is not an integration correctness or official cost PASS.',
                               'A second byte-identical build and all required physical panels remain external gates.',
                               'Every enabled optional arithmetic variant requires its own component gate.',
                               'The fixed census event is unchanged; transfer needs the new circuit equivalence audit.'])
    atomic_json(args.log_directory/'build.json', report)
    atomic_json(args.log_directory/'build-status.json', report)
    print(json.dumps({key:value for key,value in report.items() if key != 'stages'}), flush=True)


if __name__ == '__main__':
    main()
