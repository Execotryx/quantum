#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Freeze the reviewed complete paper ledger; this does not build a circuit."""
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json

HERE = Path(__file__).resolve().parent
NARROW = HERE.parents[2]
ROUND = NARROW/'arithmetic_round2'
PINS = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add(path, expected=None, size=None):
    path = path.resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None:
        assert digest == expected, str(path)
    if size is not None:
        assert len(raw) == size, str(path)
    rel = str(path.relative_to(NARROW))
    record = dict(path=rel, bytes=len(raw), sha256=digest)
    if rel in PINS:
        assert PINS[rel] == record
    PINS[rel] = record
    return record


def manifest(path, root):
    add(path)
    data = json.loads(path.read_text())
    for pin in data['files']:
        add(root/pin['path'], pin['sha256'], pin.get('bytes'))
    return data


def save(name, data):
    path = HERE/name
    assert not path.exists(), name
    path.write_text(json.dumps(data, indent=2)+'\n')
    return path


def main():
    assert not (HERE/'SOURCE_READY.json').exists()
    manifest(NARROW/'native/candidate07/INPUTS.json', NARROW)
    manifest(NARROW/'native/candidate07/SOURCE_READY.json', NARROW/'native/candidate07')
    manifest(ROUND/'PROTECTED_INTERFACES.json', NARROW)
    # Each tuple identifies a previously reviewed component and its successful
    # native guard. The explicit proof pin must also match the acceptance.
    selected = {
        'normalization': ('research/root_normalization/native_rn2df',
            'RESULT_MANIFEST.json', 'NORMALIZATION9475_NATIVE_ACCEPTED.json',
            'normalization9475.py', 'NATIVE_PROOF.json', 'guard.json', 94.75),
        'root': ('research/root_normalization/native_rn3',
            'RESULT_MANIFEST.json', 'ROOT_RN3_NATIVE_ACCEPTED.json',
            'root192.py', 'root192_native_proof.json', 'native.guard.json', 192),
        'divider': ('research/divider/native_ar004',
            'MANIFEST_RESULTS.json', 'DIVIDER_HISTORY12_NATIVE_ACCEPTED.json',
            'adapter.py', 'NATIVE_PROOF.json', 'native.guard.json', 578),
        'product': ('research/product_coefficient/native_v3',
            'RESULT_MANIFEST.json', 'PRODUCT_V3_NATIVE_ACCEPTED.json',
            'adapter.py', 'result/PROOF.json',
            'native.guard.json', 228.5),
        'coefficient': ('research/product_coefficient',
            'TOP_TRANSFER_RESULT_MANIFEST.json', 'COEFFICIENT_TOP_NATIVE_ACCEPTED.json',
            'native_transfer.py', 'top_transfer_native/PROOF.json',
            'top_transfer_native_attempt02.guard.json', 118),
    }
    proofs, adapters = {}, {}
    for name, (directory, result_name, receipt, adapter, proof, guard, count) in selected.items():
        base = ROUND/directory
        anchor = NARROW if name == 'product' else base
        records = manifest(base/result_name, anchor)
        acceptance = add(ROUND/'receipts'/receipt)
        accepted = json.loads((ROUND/'receipts'/receipt).read_text())
        assert accepted['status'] == 'PARENT_REVIEW_ACCEPTED_NATIVE_COMPONENT_FOR_COMPOSITION'
        assert accepted['result_manifest_sha256'] == sha(base/result_name)
        proof_sha = accepted.get('native_proof_sha256', accepted.get('proof_sha256'))
        assert sha(base/proof) == proof_sha
        successful = json.loads((base/guard).read_text())
        assert successful['status'] == 'COMPLETED' and successful['returncode'] == 0
        assert successful['child_cleanup']['complete']
        assert successful['work_window_sha256'] == '18a44534df9aaa46f4ab3bcaeb452e46cad3a7bd317a0edf798ee37ecde622fe'
        if 'guard_sha256' in accepted:
            assert accepted['guard_sha256'] == sha(base/guard)
        if (base/'INPUTS.json').exists():
            manifest(base/'INPUTS.json', NARROW)
        if (base/'SOURCE_READY.json').exists():
            manifest(base/'SOURCE_READY.json', anchor)
        for row in records['files']:
            if row['path'].endswith('SOURCE_READY.json'):
                manifest(anchor/row['path'], anchor)
        add(base/adapter)
        adapters[name] = str((base/adapter).relative_to(NARROW))
        proofs[name] = dict(native_acceptance=acceptance,
            result_manifest=add(base/result_name), component_expected_Toffolis=count,
            native_proof_sha256=proof_sha, guard_sha256=sha(base/guard))
    for path in [ROUND/'WORK_WINDOW.json', ROUND/'tools/strict_guard.py',
        ROUND/'tools/strict_official_guard.py', NARROW/'native/run_official_suite.py',
        NARROW/'native/candidate01/verify_official.py',
        NARROW/'native/candidate07/candidate07.build.json',
        NARROW/'native/candidate07/whole_native_text_all.json',
        NARROW/'native/candidate07/official1792/qualification.json',
        ROUND/'receipts/CANDIDATE08_IMPORT_FAILURE.json',
        ROUND/'native/candidate08/SOURCE_READY.json',
        ROUND/'native/candidate08/native_batch.guard.json']:
        add(path)
    components = dict(normalization=94.75, consuming_root=192, divider=578,
        residual_product=228.5, coefficient_arithmetic=118, seed=17.5,
        root_frames=4, metadata=7, retired_root_restoration=21,
        first_loader=61, second_loader=79, shared_table_cleanup=9, phase_endpoint=139)
    assert sum(components.values()) == 1548.75
    peaks = [
        ('normalization', dict(input=22, flags=4), 20, 46),
        ('consuming_root', dict(input_or_root_residual=22, flags=4), 13, 39),
        ('first_loader', dict(root=12, residual=10, flags=4, D=13, H=3), 6, 48),
        ('first_coefficient', dict(root=12, residual=10, flags=4, D=13, H=5, snapshot=1), 3, 48),
        ('product_forward', dict(root=12, word=16, flags=4, D=13), 3, 48),
        ('phase_endpoint_and_divider_inverse', dict(root=12, remainder=14, history=13, flags=4), 5, 48),
        ('second_loader', dict(retained_root=8, product=15, flags=4, D=13, H=3), 5, 48),
        ('second_coefficient', dict(retained_root=7, product=15, flags=4, D=13, H=5, snapshot=1), 3, 48),
        ('inverse_product_after_v3_retirement', dict(retained_root=6, word=16, flags=4, D=13, H=3, snapshot=1), 5, 48),
        ('v3_restoration', dict(retained_root=7, word=16, flags=4, D=13, H=3, snapshot=1), 0, 44),
        ('coefficient_inverse', dict(retained_root=7, residual=10, flags=4, D=13, H=5, snapshot=1), 5, 45),
        ('root_decoder', dict(restored_root=12, residual=10, flags=4, A=13, H=5), 0, 44),
    ]
    for _, data, scratch, peak in peaks:
        assert sum(data.values())+scratch == peak
    gate = dict(status='COMPLETE_POSITIVE_PAPER_COMPOSITION_GATE_NOT_WHOLE_NATIVE_OR_OFFICIAL',
        utc=datetime.now(timezone.utc).isoformat(), candidate='candidate10', Q=48,
        expected_Toffolis=1548.75, T=4, R=33, rotation_charge=230.84805946161188,
        expected_cost=48*(1548.75+1+230.84805946161188), saving_from_candidate07_E=35.25,
        components_expected_Toffolis=components,
        first_preparation_peak=48, second_preparation_peak=48, endpoint_peak=48,
        peak_ledger=[dict(stage=stage, data=data, scratch_upper_bound=scratch, peak=peak)
                     for stage, data, scratch, peak in peaks],
        original_exact_minimum_margin_units64=124370688,
        original_worst_error_to_tolerance=0.973575996935943,
        independent_phase_units50_sha256='8bd482a8957cd387a2b212afdaca656947b7f89c983d67ff4eea4e14c3b0a26a',
        accuracy_receipt_sha256='c0eab1edd234e32d5baa1a51a0fec46abf82165d3973ffda825d2149f67f11e5',
        original_tolerance_unchanged=True, protected_phase_tables_angles_oracle_unchanged=True,
        all_new_component_HMR_phases_accounted=True, all_old_carry_and_table_debts_preserved=True,
        component_native_proofs=proofs, adapter_paths=adapters,
        composition_current_handles_and_module_isolation_required=True,
        whole_native_proof_required=True, original_exact50_checker_required=True,
        official_salts=['default', 1, 2, 3], official_batch_size=256,
        actual_verifier_command_must_omit_batch_size=True, report_maximum_four_salt_cost=True,
        official_verified=False, no_submission=True, copyright='Copyright 2026 Syed Asad Ali',
        license='Apache-2.0', credits=['Opus', 'Astra'])
    gate_path = save('COMPLETE_GATE.json', gate)
    save('PARENT_ACCEPTED.json', dict(status='PARENT_ACCEPTED_COMPLETE_PAPER_GATE_FOR_NATIVE_COMPOSITION',
        utc=datetime.now(timezone.utc).isoformat(), complete_gate_sha256=sha(gate_path),
        native_build_authorized=True, all_selected_components_native_proved=True,
        protected_phase_and_loaders_unchanged=True, whole_native_and_four_default_batch_salts_required=True,
        no_official_or_full_circuit_success_claim=True))
    source = HERE/'arithmetic_variant.py'
    text = source.read_text()
    assert text.count('PENDING_COMPLETE_COMPOSITION_REVIEW') == 1
    source.write_text(text.replace('PENDING_COMPLETE_COMPOSITION_REVIEW', sha(gate_path)))
    save('INPUTS.json', dict(status='TRANSITIVE_FROZEN_COMPONENT_AND_BASELINE_INPUTS',
        files=[PINS[key] for key in sorted(PINS)]))
    names = ['arithmetic_variant.py', 'generate.py', 'prove50.py', 'native_batch.py', 'lifecycle10.py',
             'freeze_gate.py', 'README.md', 'COMPLETE_GATE.json', 'PARENT_ACCEPTED.json', 'INPUTS.json']
    for name in names:
        if name.endswith('.py'):
            ast.parse((HERE/name).read_text())
    ready = save('SOURCE_READY.json', dict(status='FROZEN_NATIVE_COMPOSITION_SOURCE_READY',
        files=[dict(path=name, bytes=(HERE/name).stat().st_size, sha256=sha(HERE/name)) for name in names],
        all_selected_components_native_proved=True, whole_native_and_official_pending=True,
        fresh_window_guard_required=True))
    print(json.dumps(dict(gate_sha256=sha(gate_path), source_ready_sha256=sha(ready),
        inputs_sha256=sha(HERE/'INPUTS.json'), input_files=len(PINS),
        expected_cost=gate['expected_cost']), indent=2))


if __name__ == '__main__':
    main()
