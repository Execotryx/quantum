# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Actual loaded sources and fail-closed component gates for a new v6 tape.

The frozen v4 source inventory/component manifest and both v5 source packets
are preserved. They are provenance dependencies, not new-v6 official results.
All eleven required full gates must exist before native-dependent providers are
loaded. No accepted source map is rewritten to admit the new providers.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
from v6_paths import HERE, ROOT, WORK

V4 = WORK/'after_v3/integration_v4'
INITIAL = WORK/'after_v3/integration_v5'
V5B = WORK/'after_v3/integration_v5b'
V5B_MANIFEST_SHA = 'b15aa9cfa6cfee388adfd0e544807ef09ab5f5ca788a3f37b13641bb14be53d6'
V5B_PLAN_SHA = 'a456fd4a9cc229ecc5b2c36612e0777c890e49019db2a348d02e81d6ab44b617'
INITIAL_MANIFEST_SHA = '6c347cbd1bd5c836d9e56f272f20a44f805103db85b7e72b945e42825be7f9ba'
INITIAL_PLAN_SHA = '0b4932be57dadb5ea3f70794d7635ed9b5db09a34f4ed4a05e5a3acf6d4b0518'
V4_MANIFEST_SHA = 'd6918c9937e961a5610423012713ef65edcd7fe545ad19e4612cce922144dc1c'
V4_INVENTORY_SHA = 'cdc992beb448848f14864875cf7989ffb04ccd135a2a2162afafd991034574f6'
V4_SOURCE_MAP_SHA = '0fc6519e8567b120dfcce839af706c2c773680ba7edfc2e32cff7558bd5c0660'
ADDITIONAL_COMPONENTS = {
    'retained_norm195_isolated', 'first_two_retained_norm_production_key',
    'transpose14_isolated', 'transpose14_preimage',
    'matched_norm_debts_isolated', 'first_two_matched_norm_production_key',
    'cubic20_isolated', 'quotient62_isolated', 'quotient62_transpose14_preimage',
    'third_zero_repaired_isolated', 'first_three_zero_repaired_production_key',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    tmp.replace(path)


def checked_path(name):
    path = Path(name)
    assert not path.is_absolute() and path.as_posix() == name and '..' not in path.parts
    result = (ROOT/path).resolve()
    assert result.is_relative_to(ROOT) and result.is_file(), name
    return result


def _check_files(files):
    for name, row in files.items():
        source = checked_path(name)
        assert source.stat().st_size == row['bytes'] and digest(source) == row['sha256'], name


def verify_frozen_v4():
    """Rehash only sources/receipts; never read the old compiled tape."""
    path = V4/'NATIVE_COMPONENT_GATES.json'
    assert digest(path) == V4_MANIFEST_SHA
    manifest = json.loads(path.read_text())
    assert manifest['format'] == 'DQI_V4_COMPONENT_NATIVE_GATES_V1'
    assert manifest['status'] == 'ALL_SELECTED_COMPONENT_GATES_PASSED'
    assert len(manifest['components']) == 17 and len(manifest['files']) == 163
    assert manifest['new_population_event'] is False
    _check_files(manifest['files'])
    for row in manifest['components']:
        assert row['full_gate'] is True
        assert row['report'] in manifest['files'] and row['guard'] in manifest['files']
        report = json.loads(checked_path(row['report']).read_text())
        guard = json.loads(checked_path(row['guard']).read_text())
        assert report['status'] == row['passed_status'] and report['status'].startswith('PASS_')
        assert guard['status'] == 'complete' and guard['exit_code'] == 0 and guard['stopped'] is False
    inventory_path = V4/'runs/a/build/source-inventory.json'
    assert digest(inventory_path) == V4_INVENTORY_SHA
    inventory = json.loads(inventory_path.read_text())
    assert inventory['format'] == 'DQI_AFTER_V3_LOADED_SOURCE_BINDING_V4'
    records = {row['path']: row for row in inventory['files']}
    assert len(records) == len(inventory['files']) == inventory['file_count'] == 112
    assert canonical_digest(records) == inventory['source_map_sha256'] == V4_SOURCE_MAP_SHA
    _check_files(records)
    return dict(status='FROZEN_V4_SOURCES_AND_COMPONENT_RECEIPTS_PRESERVED',
                component_manifest=dict(path=str(path.relative_to(ROOT)), sha256=V4_MANIFEST_SHA,
                                        components=17, pinned_files=163),
                source_inventory=dict(path=str(inventory_path.relative_to(ROOT)),
                                      sha256=V4_INVENTORY_SHA, files=112,
                                      source_map_sha256=V4_SOURCE_MAP_SHA),
                old_compiled_tape_read=False, old_official_results_used_as_v6=False)


def verify_frozen_initial_v5():
    """Preserve its source preparation without requiring an initial-v5 tape."""
    path = INITIAL/'SOURCE_MANIFEST.json'
    assert digest(path) == INITIAL_MANIFEST_SHA
    packet = json.loads(path.read_text())
    assert packet['format'] == 'DQI_FIXED_V5_SOURCE_PREPARATION_PACKET_V1'
    assert packet['status'] == 'SOURCE_REVIEWED_NEW_NATIVE_GATES_PENDING'
    assert len(packet['files']) == 17 and packet['required_new_component_gates'] == 4
    records = {str((INITIAL/name).relative_to(ROOT)):row for name,row in packet['files'].items()}
    _check_files(records)
    plan_path = INITIAL/'COMPONENT_GATE_PLAN.json'
    assert digest(plan_path) == INITIAL_PLAN_SHA
    plan = json.loads(plan_path.read_text())
    assert plan['format'] == 'DQI_V5_COMPONENT_GATE_PLAN_V1'
    assert plan['status'] == 'SOURCE_PLAN_NOT_NATIVE_EVIDENCE'
    assert len(plan['source_files']) == 39
    _check_files(plan['source_files'])
    for name,sha in packet['independent_reviews'].items():
        assert digest(checked_path(name)) == sha
    return dict(status='FROZEN_INITIAL_V5_SOURCE_PREPARATION_PRESERVED',
                source_packet=dict(path=str(path.relative_to(ROOT)),sha256=INITIAL_MANIFEST_SHA,files=17),
                source_plan=dict(path=str(plan_path.relative_to(ROOT)),sha256=INITIAL_PLAN_SHA,pinned_files=39),
                initial_v5_native_manifest_or_tape_required=False,
                initial_v5_official_results_used_as_v6=False)


def verify_frozen_v5b():
    """Preserve the fallback source packet without assuming a v5b tape."""
    path = V5B/'SOURCE_MANIFEST.json'
    assert digest(path) == V5B_MANIFEST_SHA
    packet = json.loads(path.read_text())
    assert packet['format'] == 'DQI_FIXED_V5B_SOURCE_PREPARATION_PACKET_V1'
    assert packet['status'] == 'SOURCE_REVIEWED_NEW_NATIVE_GATES_PENDING'
    assert len(packet['files']) == 21 and packet['required_new_component_gates'] == 9
    records = {str((V5B/name).relative_to(ROOT)):row for name,row in packet['files'].items()}
    _check_files(records)
    plan_path = V5B/'COMPONENT_GATE_PLAN.json'
    assert digest(plan_path) == V5B_PLAN_SHA
    plan = json.loads(plan_path.read_text())
    assert plan['format'] == 'DQI_V5B_COMPONENT_GATE_PLAN_V1'
    assert plan['status'] == 'SOURCE_PLAN_NOT_NATIVE_EVIDENCE'
    assert len(plan['source_files']) == 78
    _check_files(plan['source_files'])
    for name,sha in packet['independent_reviews'].items():
        assert digest(checked_path(name)) == sha
    return dict(status='FROZEN_V5B_SOURCE_PREPARATION_PRESERVED',
                source_packet=dict(path=str(path.relative_to(ROOT)),sha256=V5B_MANIFEST_SHA,files=21),
                source_plan=dict(path=str(plan_path.relative_to(ROOT)),sha256=V5B_PLAN_SHA,pinned_files=78),
                v5b_native_manifest_or_tape_required=False,
                all_nine_v5b_component_gates_revalidated_by_v6=True,
                v5b_official_results_used_as_v6=False)


def verify_components():
    assert __debug__ and sys.version_info[:2] == (3,13)
    parent = verify_frozen_v4()
    initial = verify_frozen_initial_v5()
    fallback = verify_frozen_v5b()
    plan_path = HERE/'COMPONENT_GATE_PLAN.json'
    plan = json.loads(plan_path.read_text())
    assert plan['format'] == 'DQI_V6_COMPONENT_GATE_PLAN_V1'
    assert plan['status'] == 'SOURCE_PLAN_NOT_NATIVE_EVIDENCE'
    assert set(row['name'] for row in plan['components']) == ADDITIONAL_COMPONENTS
    assert len(plan['components']) == len(ADDITIONAL_COMPONENTS)
    assert plan['new_population_event'] is False
    _check_files(plan['source_files'])
    # Deliberately absent until the separate receipt producer validates every
    # full native gate. A source plan or smoke result cannot enable emission.
    path = HERE/'NATIVE_COMPONENT_GATES.json'
    manifest = json.loads(path.read_text())
    assert manifest['format'] == 'DQI_V6_COMPONENT_NATIVE_GATES_V1'
    assert manifest['status'] == 'ALL_SELECTED_COMPONENT_GATES_PASSED'
    assert manifest['new_population_event'] is False
    assert manifest['plan_sha256'] == digest(plan_path)
    assert manifest['producer_sha256'] == digest(HERE/'prepare_component_gates.py')
    assert manifest['frozen_v4'] == parent
    assert manifest['frozen_initial_v5'] == initial
    assert manifest['frozen_v5b'] == fallback
    assert {row['name'] for row in manifest['components']} == ADDITIONAL_COMPONENTS
    assert len(manifest['components']) == len(ADDITIONAL_COMPONENTS)
    _check_files(manifest['files'])
    for name, wanted in plan['source_files'].items():
        assert manifest['files'][name] == wanted
    assert str(plan_path.relative_to(ROOT)) in manifest['files']
    assert str((HERE/'prepare_component_gates.py').relative_to(ROOT)) in manifest['files']
    planned = {row['name']: row for row in plan['components']}
    for row in manifest['components']:
        wanted = planned[row['name']]
        assert row['full_gate'] is True
        assert (row['report'], row['guard'], row['passed_status']) == (
            wanted['report'], wanted['guard'], wanted['passed_status'])
        assert row['report'] in manifest['files'] and row['guard'] in manifest['files']
        report = json.loads(checked_path(row['report']).read_text())
        guard = json.loads(checked_path(row['guard']).read_text())
        assert report['status'] == row['passed_status'] and report['status'].startswith('PASS_')
        assert guard['status'] == 'complete' and guard['exit_code'] == 0 and guard['stopped'] is False
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
                component_count=len(manifest['components']), pinned_files=len(manifest['files']),
                plan_sha256=manifest['plan_sha256'], status=manifest['status'],
                frozen_v4=parent, frozen_initial_v5=initial, frozen_v5b=fallback)


def verify_preservation(runtime):
    import accepted_runtime as Accepted
    assert Accepted.pinned_sources() == runtime.pinned_sources
    assert runtime.bootstrap.validate_normalization() == runtime.derivation
    assert runtime.binding.verify_accepted_sources() == runtime.baseline_binding
    return dict(accepted_base_pins=runtime.pinned_sources,
                accepted_base_gate=runtime.baseline_binding,
                normalization_derivation=runtime.derivation,
                selected_components=verify_components())


def entrypoint_audit():
    expected = {
        'gen_dqi.py': {'--output', '--log-directory', '--rss-soft', '--available-reserve'},
        'build_v6.py': {'--output', '--log-directory', '--engineering-scan-positions'},
    }
    rows = {}
    for name, wanted in expected.items():
        path = HERE/name
        tree = ast.parse(path.read_text())
        arguments = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
                arguments += [x.value for x in node.args if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        assert set(arguments) == wanted and len(arguments) == len(wanted), (name, arguments)
        rows[name] = dict(sha256=digest(path), options=sorted(arguments))
    return dict(status='PASS_FIXED_PUBLIC_ARGUMENT_SURFACE', files=rows,
                production_positions=4095, public_cutoff=15,
                profile_terminal_contacts_aliases_salt_parameters=[])


def write_inventory(path, pipeline, before, after):
    assert before == after
    records = {}

    def add(source, module=None, role=None):
        source = Path(source).resolve()
        assert source.is_relative_to(ROOT) and source.is_file(), source
        name = str(source.relative_to(ROOT))
        row = records.setdefault(name, dict(path=name, modules=[], explicit=[]))
        if module is not None:
            row['modules'].append(module)
        if role is not None:
            row['explicit'].append(role)

    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename is None:
            continue
        source = Path(filename).resolve()
        if source.suffix == '.pyc':
            source = Path(importlib.util.source_from_cache(str(source))).resolve()
        if source.is_relative_to(WORK) or source.is_relative_to(ROOT/'pro1_controller_bundle'):
            add(source, module=name)
    for source, role in ((HERE/'gen_dqi.py', 'fixed_production_entrypoint'),
                         (HERE/'build_v6.py', 'builder_entrypoint'),
                         (HERE/'COMPONENT_GATE_PLAN.json', 'fixed_additional_gate_plan'),
                         (HERE/'NATIVE_COMPONENT_GATES.json', 'selected_native_gates'),
                         (V4/'NATIVE_COMPONENT_GATES.json', 'preserved_v4_component_manifest'),
                         (V4/'runs/a/build/source-inventory.json', 'preserved_v4_source_inventory'),
                         (INITIAL/'SOURCE_MANIFEST.json', 'preserved_initial_v5_source_packet'),
                         (INITIAL/'COMPONENT_GATE_PLAN.json', 'preserved_initial_v5_source_plan'),
                         (V5B/'SOURCE_MANIFEST.json', 'preserved_v5b_source_packet'),
                         (V5B/'COMPONENT_GATE_PLAN.json', 'preserved_v5b_source_plan'),
                         (WORK/'after_c5/root/guard_wait.py', 'one_heavy_job_memory_guard')):
        add(source, role=role)
    engine = Path(sys.modules['kickmix'].__file__).resolve()
    assert digest(engine) == 'c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e'
    add(engine, role='original_supplied_native_engine')
    for row in records.values():
        source = checked_path(row['path'])
        row.update(bytes=source.stat().st_size, sha256=digest(source),
                   modules=sorted(set(row['modules'])), explicit=sorted(set(row['explicit'])))
    value = dict(format='DQI_AFTER_V3_LOADED_SOURCE_BINDING_V6',
                 status='CAPTURED_NEW_CANDIDATE_SOURCE_BINDING',
                 files=[records[k] for k in sorted(records)], file_count=len(records),
                 source_map_sha256=canonical_digest(records),
                 python=sys.version, executable=sys.executable,
                 preservation_and_component_gates=after,
                 entrypoint_audit=entrypoint_audit(),
                 runtime_bindings=pipeline.runtime_bindings(),
                 finish_geometry_binding=pipeline.finish_geometry_binding(),
                 scope='Actual new imports and fixed helper identities; no old source-map equality or official PASS inferred.')
    atomic_json(path, value)
    return dict(path=str(Path(path).resolve()), sha256=digest(path),
                source_map_sha256=value['source_map_sha256'], files=len(records),
                status=value['status'])


def validate_inventory(reference):
    path = Path(reference['path']).resolve()
    assert path.is_relative_to(ROOT) and path.is_file()
    assert digest(path) == reference['sha256']
    inventory = json.loads(path.read_text())
    assert inventory['format'] == 'DQI_AFTER_V3_LOADED_SOURCE_BINDING_V6'
    assert inventory['status'] == 'CAPTURED_NEW_CANDIDATE_SOURCE_BINDING'
    records = {row['path']:row for row in inventory['files']}
    assert len(records) == len(inventory['files']) == inventory['file_count']
    assert canonical_digest(records) == inventory['source_map_sha256'] == reference['source_map_sha256']
    _check_files(records)
    return inventory


def verify_receipt_preservation(wanted):
    """Pure source/receipt check; imports no native engine or circuit."""
    directory = WORK/'after_c5/integration_v3'
    if str(directory) not in sys.path:
        sys.path.insert(0,str(directory))
    import source_binding as OldBinding
    assert Path(OldBinding.__file__).resolve() == directory/'source_binding.py'
    import accepted_runtime as Accepted
    spec = importlib.util.spec_from_file_location('v6_readonly_release_derivation',Accepted.RELEASE/'build_release.py')
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    result = dict(accepted_base_pins=Accepted.pinned_sources(),
                  accepted_base_gate=OldBinding.verify_accepted_sources(),
                  normalization_derivation=bootstrap.validate_normalization(),
                  selected_components=verify_components())
    assert result == wanted
    return result
