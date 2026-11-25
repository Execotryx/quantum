#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Build one fixed DQI candidate under the external runtime memory guard.

Engineering partial scans are explicitly marked incomplete. Only a full scan
can become a deliverable after the external C2--C5 checks have passed. This
builder does not submit, select a verification salt, or receive input profiles.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import sys
import time

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parent
for directory in (ROOT/'pro1_controller_bundle/1_task/official', HERE/'synthesis',
                  HERE/'arithmetic', HERE/'controller'):
    sys.path.insert(0, str(directory))


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--log-directory', type=Path, required=True)
    p.add_argument('--engineering-scan-positions', type=int, default=4095)
    p.add_argument('--conditional-flag-phases', action='store_true')
    a = p.parse_args()
    assert 0 < a.engineering_scan_positions <= 4095
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.log_directory.mkdir(parents=True, exist_ok=True)
    import kickmix as km
    import fixed_pipeline as Pipeline
    if a.conditional_flag_phases:
        import rolling_tail_conditional as Conditional
        import raw_query_extractor as Extractor
        Pipeline.Tail = Conditional
        Extractor.Tail = Conditional
    started = time.monotonic()
    builder = km.CircuitBuilder()
    builder.set_max_qubits(890)
    S = [builder.create_quantum_register(12, f'S{i}') for i in range(70)]
    E = [builder.create_classical_register(12, f'E{i}') for i in range(4095)]
    stages = []
    status_path = a.log_directory/'build-status.json'

    def stage(message):
        row = dict(stage=message, elapsed_seconds=time.monotonic()-started,
                   allocated_Q=builder.num_allocated_qubits)
        stages.append(row)
        atomic_json(status_path, dict(status='BUILDING', last=row, completed_stages=stages))
        print(json.dumps(row), flush=True)

    contract = Pipeline.emit(builder, S, E, j_min=15,
                             scan_positions=a.engineering_scan_positions, stage=stage)
    assert builder.num_allocated_qubits == 840
    circuit = builder.finish_circuit()
    del builder
    gc.collect()
    static_T = circuit.operation_statistics().num_toffoli_like
    expected = 390556 - 44275 + contract['scan']['static_T']
    assert static_T == expected, (static_T, expected)
    assert circuit.num_qubits == 890, circuit.num_qubits
    temporary = a.output.with_suffix(a.output.suffix+'.tmp')
    circuit.to_file(temporary, format='kmb')
    del circuit
    gc.collect()
    temporary.replace(a.output)
    with a.output.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    from provenance.source_inventory import write_inventory
    source_inventory = write_inventory(a.log_directory/'source-inventory.json', workspace=ROOT)
    report = dict(status='BUILT_UNVERIFIED_FIXED_CANDIDATE', circuit=str(a.output.resolve()),
                  sha256=sha, bytes=a.output.stat().st_size, Q=890, static_T=static_T,
                  sampled_mean_T=None, full_DQI_scan=a.engineering_scan_positions == 4095,
                  conditional_flag_phases=a.conditional_flag_phases, contract=contract,
                  source_inventory=source_inventory,
                  elapsed_seconds=time.monotonic()-started, stages=stages,
                  limitations=['A successful build alone does not pass C2, C3, C4 or C5.',
                               'No official verifier or failure certificate is implied.'])
    atomic_json(a.log_directory/'build.json', report)
    atomic_json(status_path, report)
    print(json.dumps({k:v for k,v in report.items() if k != 'stages'}), flush=True)


if __name__ == '__main__':
    main()
