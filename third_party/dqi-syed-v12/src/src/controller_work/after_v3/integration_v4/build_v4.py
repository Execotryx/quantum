#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded fixed v4 build; the engineering scan option is not public."""
from pathlib import Path
from fractions import Fraction
import argparse
import gc
import json
import sys
import time
from v4_binding import atomic_json, digest, verify_preservation, write_inventory
import v4_pipeline as Pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--log-directory', type=Path, required=True)
    parser.add_argument('--engineering-scan-positions', type=int, default=4095)
    args = parser.parse_args()
    if not __debug__ or sys.version_info[:2] != (3,13):
        parser.error('Use ordinary Python3.13 without optimization.')
    assert __debug__ and 0 < args.engineering_scan_positions <= 4095
    args.output, args.log_directory = args.output.resolve(), args.log_directory.resolve()
    assert not args.output.exists() and not (args.log_directory/'build.json').exists()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.log_directory.mkdir(parents=True, exist_ok=True)
    Pipeline.configure()
    before = verify_preservation(Pipeline.Runtime)
    import kickmix as km
    from v4_events import Events
    events = Events()
    events.install(Pipeline)
    started = time.monotonic()
    builder = km.CircuitBuilder()
    builder.set_max_qubits(889)
    S = [builder.create_quantum_register(12, f'S{i}') for i in range(70)]
    E = [builder.create_classical_register(12, f'E{i}') for i in range(4095)]
    stages = []

    def stage(message):
        row = dict(stage=message, allocated_Q=builder.num_allocated_qubits,
                   elapsed_seconds=time.monotonic()-started)
        stages.append(row)
        atomic_json(args.log_directory/'build-status.json',
                    dict(status='BUILDING_UNVERIFIED_V4', last=row, completed_stages=stages))
        print(json.dumps(row), flush=True)

    contract = Pipeline.emit(builder, S, E, j_min=15,
                            scan_positions=args.engineering_scan_positions, stage=stage)
    assert builder.num_allocated_qubits == 840
    circuit = builder.finish_circuit()
    del builder
    gc.collect()
    static_T = circuit.operation_statistics().num_toffoli_like
    assert static_T == Pipeline.source_ledger(contract['scan']['static_T'])['total_static_T']
    assert circuit.num_qubits == 889 and dict(circuit.operation_statistics()).get('Z_POW',0) == 0
    expectation = events.snapshot(static_T, contract['scan']['point_tests'])
    assert Fraction(expectation['expected_T_exact']) == Pipeline.expected_mean(static_T,contract['scan']['point_tests']), expectation
    instructions, bits = len(circuit), circuit.num_bits
    temporary = args.output.with_suffix(args.output.suffix+'.tmp')
    assert not temporary.exists()
    circuit.to_file(temporary, format='kmb')
    del circuit
    gc.collect()
    temporary.replace(args.output)
    Pipeline.assert_bindings()
    after = verify_preservation(Pipeline.Runtime)
    inventory = write_inventory(args.log_directory/'source-inventory.json', Pipeline,before,after)
    report = dict(status='BUILT_UNVERIFIED_FIXED_V4_CANDIDATE',
                  circuit=str(args.output),sha256=digest(args.output),bytes=args.output.stat().st_size,
                  Q=889,static_T=static_T,instructions=instructions,classical_bits=bits,
                  measured_mean_T=None,nominal_cost=None,official_cost=None,
                  uniform_mask_source_expectation=expectation,
                  full_DQI_scan=args.engineering_scan_positions == 4095,
                  contract=contract,source_inventory=inventory,
                  elapsed_seconds=time.monotonic()-started,stages=stages,
                  limitations=['A new build is not a correctness or official-cost PASS.',
                    'Two identical builds, original physical panels and four original full salts are separate gates.',
                    'No old official mean, integer error count or failure factor transfers to a new tape.'])
    atomic_json(args.log_directory/'build.json',report)
    atomic_json(args.log_directory/'build-status.json',report)
    print(json.dumps({k:v for k,v in report.items() if k != 'stages'}),flush=True)


if __name__ == '__main__':
    main()
