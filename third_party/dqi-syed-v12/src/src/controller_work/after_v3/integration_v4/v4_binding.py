# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Actual loaded-source and passed-component binding for a new v4 tape.

This is a new binding format. It never claims that new source maps equal
the accepted v3 map, and never changes an old receipt to admit a new file.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
from v4_paths import HERE, ROOT, WORK


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


def verify_components():
    path = HERE/'NATIVE_COMPONENT_GATES.json'
    manifest = json.loads(path.read_text())
    assert manifest['format'] == 'DQI_V4_COMPONENT_NATIVE_GATES_V1'
    assert manifest['status'] == 'ALL_SELECTED_COMPONENT_GATES_PASSED'
    assert manifest['new_population_event'] is False
    expected = {'scan_point', 'scan_full', 'quotient_phase84_masked',
                'last_return', 'borrowed_forward_isolated', 'borrowed_forward_preimage',
                'retained_third_preimage', 'parked_scale_isolated',
                'masked_parked_scale_isolated', 'transpose_isolated',
                'combined_preimage', 'transpose_handoff_isolated',
                'transpose_handoff_preimage', 'rare_paired_isolated',
                'rare_paired_preimage', 'joint_norm_phase_isolated',
                'joint_norm_phase_preimage'}
    assert {row['name'] for row in manifest['components']} == expected
    assert len(manifest['components']) == len(expected)
    for name, row in manifest['files'].items():
        source = checked_path(name)
        assert source.stat().st_size == row['bytes'] and digest(source) == row['sha256'], name
    for row in manifest['components']:
        assert row['report'] in manifest['files']
        assert row['guard'] in manifest['files']
        report = json.loads(checked_path(row['report']).read_text())
        assert report['status'] == row['passed_status'], row['name']
        assert report['status'].startswith('PASS_')
        guard = json.loads(checked_path(row['guard']).read_text())
        assert guard['status'] == 'complete' and guard['exit_code'] == 0 and guard['stopped'] is False
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
                component_count=len(manifest['components']),
                pinned_files=len(manifest['files']), status=manifest['status'])


def verify_preservation(runtime):
    """Check old bytes and the new provider contract without old rebinding."""
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
        'build_v4.py': {'--output', '--log-directory', '--engineering-scan-positions'},
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
                         (HERE/'build_v4.py', 'builder_entrypoint'),
                         (HERE/'NATIVE_COMPONENT_GATES.json', 'selected_native_gates'),
                         (WORK/'after_c5/root/guard_wait.py', 'one_heavy_job_memory_guard')):
        add(source, role=role)
    engine = Path(sys.modules['kickmix'].__file__).resolve()
    assert digest(engine) == 'c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e'
    add(engine, role='original_supplied_native_engine')
    for row in records.values():
        source = checked_path(row['path'])
        row.update(bytes=source.stat().st_size, sha256=digest(source),
                   modules=sorted(set(row['modules'])), explicit=sorted(set(row['explicit'])))
    value = dict(format='DQI_AFTER_V3_LOADED_SOURCE_BINDING_V4',
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
    assert digest(path) == reference['sha256']
    inventory = json.loads(path.read_text())
    assert inventory['format'] == 'DQI_AFTER_V3_LOADED_SOURCE_BINDING_V4'
    assert inventory['status'] == 'CAPTURED_NEW_CANDIDATE_SOURCE_BINDING'
    records = {row['path']:row for row in inventory['files']}
    assert len(records) == len(inventory['files']) == inventory['file_count']
    assert canonical_digest(records) == inventory['source_map_sha256'] == reference['source_map_sha256']
    for name,row in records.items():
        source = checked_path(name)
        assert source.stat().st_size == row['bytes'] and digest(source) == row['sha256'], name
    return inventory


def verify_receipt_preservation(wanted):
    """Pure source/receipt check; imports no native engine or circuit."""
    directory = WORK/'after_c5/integration_v3'
    if str(directory) not in sys.path:
        sys.path.insert(0,str(directory))
    import source_binding as OldBinding
    assert Path(OldBinding.__file__).resolve() == directory/'source_binding.py'
    import accepted_runtime as Accepted
    spec = importlib.util.spec_from_file_location('v4_readonly_release_derivation',Accepted.RELEASE/'build_release.py')
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    result = dict(accepted_base_pins=Accepted.pinned_sources(),
                  accepted_base_gate=OldBinding.verify_accepted_sources(),
                  normalization_derivation=bootstrap.validate_normalization(),
                  selected_components=verify_components())
    assert result == wanted
    return result
