# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Read-only C5/v1/v2 and component gates; a separate v3 source inventory."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from integration_paths import HERE, AFTER, WORK, ROOT

CONFIG = WORK/'night_c27/census/runs/validate10000/config/config.json'
CONFIG_SHA = '7d830cc32f348e304ef015337ebff7d9ff36e0ddf412fa5f7c60c4c99b0e28e0'
CONFIG_DIGEST = 'e28a5569ac05bf651017d0be6760bbc8ffe4182510217a5c06f14381f924ca3b'
ENGINE_SHA = 'c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e'
PRIOR_INVENTORY = AFTER/'integration/runs/engineering64/build/source-inventory.json'
PRIOR_INVENTORY_SHA = '7fb7b492ae552e8300cbc256e3309a9950bfc14ea871b0470c924fa02abf9764'
PRIOR_SOURCE_MAP_SHA = '3dc7d4f685ad852c86b877ff85a4ec58bebcd7e6daaf62d86893ed9e439d5377'
PRIOR_BUILD = AFTER/'integration/runs/engineering64/build/build.json'
PRIOR_BUILD_SHA = '52440b9291d661d22add380870ca47515aa681a78978513d20fb6ba1ef1940fb'
ORIGINAL_SNAPSHOT_SHA = '9fcb88d4496e04dbc87f5dc18c480b3e50ce84b07c42e2d4ee07c44c78773e41'
V2_SNAPSHOT_SHA = 'ad3f313643ed5ec8b1ef6b2b13874f0f50b8e3db67e92086eb6624fd702216fd'
V2_INVENTORY_SHA = '36bbaf510af7f046d3d71a4c3e6c7910906078d5da73e411cc4c81ed75a410ae'
V2_SOURCE_MAP_SHA = '57f62950583c6c6dd8e4184df338367974a98afb31c6f79f66e1da7cfc8b6788'
V2_CIRCUIT_SHA = 'eaba3087364f0edbcea12c3c736480858bd152970720683e8fc780395deb7a16'
TAIL_REPORT = AFTER/'converter_width/tail_phase_defer/runs/full/report.json'
TAIL_REPORT_SHA = 'cd6b35411405f732cbc88019951aff32879a6123612539b30aaf6f8a2d5a4eea'
LOCAL_REPORT = AFTER/'converter_width/local_flag_defer/runs/full/report.json'
LOCAL_REPORT_SHA = '23adfca403f364acadabc647b2de66b29cbea661f4c2bf00d52529191cae3005'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def checked_path(name):
    path = Path(name)
    assert not path.is_absolute() and path.as_posix() == name
    assert '..' not in path.parts
    result = (ROOT/path).resolve()
    assert result.is_relative_to(ROOT) and result.is_file()
    return result


def verify_prior_integration_sources():
    """Preserve all84 source records of the already passed v1 engineering run."""
    assert digest(PRIOR_INVENTORY) == PRIOR_INVENTORY_SHA
    assert digest(PRIOR_BUILD) == PRIOR_BUILD_SHA
    build = json.loads(PRIOR_BUILD.read_text())
    inv = json.loads(PRIOR_INVENTORY.read_text())
    assert build['Q'] == 889 and build['static_T'] == 342128
    assert build['contract']['scan']['physical_positions'] == 64
    assert build['source_inventory']['sha256'] == PRIOR_INVENTORY_SHA
    assert build['source_inventory']['source_map_sha256'] == PRIOR_SOURCE_MAP_SHA
    assert inv['status'] == 'CAPTURED_NEW_CANDIDATE_SOURCE_BINDING'
    assert inv['file_count'] == len(inv['files']) == 84
    records = {row['path']: row for row in inv['files']}
    assert len(records) == 84
    assert canonical_digest(records) == inv['source_map_sha256'] == PRIOR_SOURCE_MAP_SHA
    for name, row in records.items():
        path = checked_path(name)
        assert path.stat().st_size == row['bytes'], name
        assert digest(path) == row['sha256'], ('Passed v1 source changed', name)
    snapshot_path = HERE/'ORIGINAL_INTEGRATION_SNAPSHOT.json'
    assert digest(snapshot_path) == ORIGINAL_SNAPSHOT_SHA
    snapshot = json.loads(snapshot_path.read_text())
    assert snapshot['source_files'] == len(snapshot['files']) == 9
    for row in snapshot['files']:
        path = checked_path(row['path'])
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
    return dict(status='PASS_PASSED_V1_SOURCE_IDENTITIES_ONLY',
                inventory=dict(path=relative(PRIOR_INVENTORY), sha256=PRIOR_INVENTORY_SHA),
                build_receipt=dict(path=relative(PRIOR_BUILD), sha256=PRIOR_BUILD_SHA),
                source_map_sha256=PRIOR_SOURCE_MAP_SHA, source_files=84,
                original_integration_python_files=9,
                original_integration_snapshot=dict(path=relative(snapshot_path),
                                                   sha256=ORIGINAL_SNAPSHOT_SHA),
                files=records,
                scope='Preserves prior source evidence; no v2 native result is inferred.')


def verify_v2_integration_sources():
    """Preserve all86 A/B runtime files and the nine current v2 source files."""
    snapshot_path = HERE/'V2_SOURCE_SNAPSHOT.json'
    assert digest(snapshot_path) == V2_SNAPSHOT_SHA
    snapshot = json.loads(snapshot_path.read_text())
    assert snapshot['status'] == 'SNAPSHOT_V2_SOURCE_AND_RECEIPT_BYTES_ONLY'
    assert len(snapshot['files']) == 9 and len(snapshot['receipt_files']) == 5
    rows = snapshot['files'] + snapshot['receipt_files']
    assert len({row['path'] for row in rows}) == 14
    for row in rows:
        path = checked_path(row['path'])
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], row['path']
    maps = []
    builds = []
    for label in ('a', 'b'):
        directory = AFTER/'integration_v2/runs'/label/'build'
        inventory_path = directory/'source-inventory.json'
        assert digest(inventory_path) == V2_INVENTORY_SHA
        inv = json.loads(inventory_path.read_text())
        build = json.loads((directory/'build.json').read_text())
        assert build['Q'] == 889 and build['static_T'] == 385653
        assert build['full_DQI_scan'] is True and build['sha256'] == V2_CIRCUIT_SHA
        assert build['source_inventory']['sha256'] == V2_INVENTORY_SHA
        assert build['source_inventory']['source_map_sha256'] == V2_SOURCE_MAP_SHA
        assert inv['status'] == 'CAPTURED_NEW_CANDIDATE_SOURCE_BINDING'
        assert inv['file_count'] == len(inv['files']) == 86
        records = {row['path']: row for row in inv['files']}
        assert len(records) == 86
        assert canonical_digest(records) == inv['source_map_sha256'] == V2_SOURCE_MAP_SHA
        maps.append(records)
        builds.append(dict(path=relative(directory/'build.json'),
                           sha256=digest(directory/'build.json')))
    assert maps[0] == maps[1]
    for name, row in maps[0].items():
        path = checked_path(name)
        assert path.stat().st_size == row['bytes'], name
        assert digest(path) == row['sha256'], ('Preserved v2 source changed', name)
    equality_path = AFTER/'integration_v2/runs/build-equality.json'
    equality = json.loads(equality_path.read_text())
    assert equality['status'] == 'PASS_NEW_CANDIDATE_BYTE_SOURCE_STAGE_EQUALITY'
    assert equality['byte_identical'] is True and equality['source_and_runtime_bindings_identical'] is True
    assert equality['source_file_count'] == 86
    assert equality['source_map_sha256'] == V2_SOURCE_MAP_SHA
    assert equality['circuit_sha256'] == V2_CIRCUIT_SHA
    return dict(status='PASS_PRESERVED_V2_SOURCE_AND_EQUALITY_RECEIPTS',
                source_files=86, source_map_sha256=V2_SOURCE_MAP_SHA,
                current_python_files=9,
                snapshot=dict(path=relative(snapshot_path), sha256=V2_SNAPSHOT_SHA),
                build_receipts=builds,
                equality_receipt=dict(path=relative(equality_path), sha256=digest(equality_path)),
                files=maps[0],
                scope='No circuit is loaded or rerun; this identity gate is not a v3 native result.')


def verify_deferred_component_gates():
    """Refuse v3 emission unless both exact full native component receipts pass."""
    assert digest(TAIL_REPORT) == TAIL_REPORT_SHA
    assert digest(LOCAL_REPORT) == LOCAL_REPORT_SHA
    tail = json.loads(TAIL_REPORT.read_text())
    local = json.loads(LOCAL_REPORT.read_text())
    assert tail['status'] == 'PASS_NATIVE_DEFERRED_TAIL_KEY_COMPONENT_ONLY'
    assert tail['cases'] == 783 and tail['physical_cases'] == 781
    assert tail['algebraic_initial_carry_cases'] == 2
    assert tail['builds_identical'] is True and tail['complete_pair_phase_checked'] is True
    assert tail['open_prefix_phase_checked'] is False
    tm = tail['metrics']
    assert tm['component_static_T'] == 152173 and tm['Q'] == 889
    assert tm['delta_static_T'] == -418 and tm['delta_uniform_fresh_mask_mean_T'] == -209
    assert tm['pending_tail_masks_after_pair'] == 0
    assert tm['created_tail_mask_indices'] == list(range(16, 35))
    assert tm['retired_tail_mask_indices'] == list(range(34, 15, -1))
    pair_runs = [row for row in tail['runs'] if row['panel'] == 'pair']
    assert len(pair_runs) == 3 and {row['seed'] for row in pair_runs} == {317, 1317, 2317}
    assert all(row['status'] == 'PASS' and row['cases'] == 783 and row['phase_errors'] == []
               for row in pair_runs)
    assert all(row['status'] == 'PASS' for row in tail['runs'])
    assert local['status'] == 'PASS_NATIVE_SAME_HALF_LOCAL_FLAG_DEFERRAL_COMPONENT_ONLY'
    assert local['fixtures'] == 256 and local['two_identical_builds'] is True
    assert local['fixture_source']['smoke'] is False and local['fixture_source']['omissions'] == []
    assert local['gauge_charts'] == [0, 1]
    lm = local['metrics']
    assert lm['static_T'] == 115627 and lm['Q'] == 889
    assert lm['delta_static_T'] == -320 and lm['delta_uniform_fresh_mask_mean_T'] == -160
    assert lm['pending_local_masks_after_pair'] == 0
    assert len(lm['created_local_debts']) == len(lm['retired_local_debts']) == 32
    assert set(map(tuple, lm['created_local_debts'])) == {
        (direction, n) for direction in (False, True) for n in range(2, 18)}
    assert sorted(lm['created_local_debts']) == sorted(lm['retired_local_debts'])
    assert len(local['roundtrip']) == len(local['prefix_values']) == 3
    assert {row['seed'] for row in local['roundtrip']} == {137, 1137, 2137}
    for row in local['roundtrip'] + local['prefix_values']:
        assert row['shots'] == 256 and row['value_restoration_scratch_errors'] == 0
        assert row['bad_value_indices'] == [] and row['bad_phase_indices'] == []
        assert row['phase_errors'] == (None if row['prefix_values_only'] else 0)
    binding_maps = {}
    for name, report in (('tail', tail), ('local', local)):
        records = report['source_bindings']
        for key, row in records.items():
            assert key == row['path']
            path = checked_path(key)
            assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], key
        binding_maps[name] = dict(files=len(records), source_map_sha256=canonical_digest(records))
    return dict(status='PASS_HASH_BOUND_NATIVE_COMPONENT_GATES_ONLY',
                tail=dict(path=relative(TAIL_REPORT), sha256=TAIL_REPORT_SHA,
                          circuit_sha256=tail['circuit_sha256'], cases=783, seeds=3,
                          static_T=152173, Q=889),
                local=dict(path=relative(LOCAL_REPORT), sha256=LOCAL_REPORT_SHA,
                           circuit_sha256=local['circuit_sha256'], cases=256, seeds=3,
                           static_T=115627, Q=889),
                component_source_bindings=binding_maps,
                static_delta_T=-738, uniform_fresh_mask_mean_delta_T=-369,
                scope='Existing component receipts only; no v3 build, joined check, salt or new failure bound is inferred.')


def verify_accepted_sources():
    """Do not read any census state or rerun its classifier or sampler."""
    binding_path = AFTER/'C6_BASELINE_BINDING.json'
    binding = json.loads(binding_path.read_text())
    assert binding['status'] == 'C5_ACCEPTED_REFERENCE_SOURCE_BINDINGS_MATCH'
    entries = binding['source_files']
    assert len(entries) == 66 and len({r['path'] for r in entries}) == 66
    checked = {}
    for row in entries:
        path = checked_path(row['path'])
        assert path.stat().st_size == row['bytes'], row['path']
        actual = digest(path)
        assert actual == row['sha256'], ('C5 source changed', row['path'])
        checked[row['path']] = actual
    assert digest(CONFIG) == CONFIG_SHA
    config = json.loads(CONFIG.read_text())
    assert config['configuration_digest'] == CONFIG_DIGEST
    frozen = config['payload']['source_sha256']
    assert len(frozen) == 14
    for name, expected in frozen.items():
        assert digest(checked_path(name)) == expected, ('Frozen source changed', name)
    return dict(status='PASS_ACCEPTED_C5_AND_FROZEN_SOURCE_BINDINGS',
                baseline_binding=dict(path=relative(binding_path), sha256=digest(binding_path)),
                accepted_source_files=checked, frozen_source_files=frozen,
                accepted_source_count=66, frozen_source_count=14,
                frozen_config=dict(path=relative(CONFIG), sha256=CONFIG_SHA,
                                   configuration_digest=CONFIG_DIGEST),
                prior_integration_sources=verify_prior_integration_sources(),
                preserved_v2_sources=verify_v2_integration_sources(),
                deferred_component_gates=verify_deferred_component_gates(),
                classifier_or_population_draws_run=False,
                scope='File identity only; new candidate correctness and failure transfer are separate gates')


def entrypoint_audit():
    files = {}
    options = {}
    expected = {
        'gen_dqi.py': {'--output','--log-directory','--rss-soft','--available-reserve',
                       '--first-two-charts','--nested-norm','--finish-seam',
                       '--infinity3-finish'},
        'build_candidate.py': {'--output','--log-directory','--engineering-scan-positions',
                              '--first-two-charts','--nested-norm','--finish-seam',
                              '--infinity3-finish'},
    }
    for name, allowed in expected.items():
        path = HERE/name
        text = path.read_text()
        tree = ast.parse(text, filename=str(path))
        flags = set()
        parse_calls = 0
        for item in ast.walk(tree):
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
                if item.func.attr == 'add_argument':
                    flags.update(ast.literal_eval(arg) for arg in item.args)
                if item.func.attr == 'parse_args':
                    parse_calls += 1
                assert item.func.attr not in ('parse_known_args','getenv')
            assert not (isinstance(item, ast.Attribute) and item.attr == 'environ')
        assert flags == allowed and parse_calls == 1, (name, flags)
        files[name] = dict(path=relative(path), sha256=digest(path), bytes=path.stat().st_size)
        options[name] = sorted(flags)
        if name == 'gen_dqi.py':
            commands = [item.value for item in ast.walk(tree)
                        if isinstance(item, ast.Assign) and any(
                            isinstance(target, ast.Name) and target.id == 'command'
                            for target in item.targets)]
            assert len(commands) == 1 and isinstance(commands[0], ast.List)
            literals = [node.value for node in ast.walk(commands[0])
                        if isinstance(node, ast.Constant) and isinstance(node.value, str)]
            assert 'runtime/guard.py' in literals and 'build_candidate.py' in literals
            assert '--engineering-scan-positions' not in literals
            stars = [node for node in commands[0].elts if isinstance(node, ast.Starred)]
            assert len(stars) == 1 and isinstance(stars[0].value, ast.Name)
            assert stars[0].value.id == 'public_flags'
        else:
            emits = [item for item in ast.walk(tree) if isinstance(item, ast.Call)
                     and isinstance(item.func, ast.Attribute) and item.func.attr == 'emit'
                     and isinstance(item.func.value, ast.Name) and item.func.value.id == 'Pipeline']
            assert len(emits) == 1
            keywords = {kw.arg: ast.unparse(kw.value) for kw in emits[0].keywords}
            assert keywords['j_min'] == '15'
            assert keywords['scan_positions'] == 'args.engineering_scan_positions'
    pipeline = HERE/'integrated_pipeline.py'
    files[pipeline.name] = dict(path=relative(pipeline), sha256=digest(pipeline),
                                bytes=pipeline.stat().st_size)
    return dict(status='PASS_PUBLIC_ARGUMENT_SURFACE_AUDIT', files=files, options=options,
                public_cutoff=15, generator_physical_positions=4095,
                profile_terminal_contacts_aliases_salt_parameters=[],
                scope='Argument and immutable-file checks, not semantic proof of downstream arithmetic')


def write_inventory(path, pipeline, accepted_before, accepted_after):
    assert accepted_before == accepted_after
    records = {}

    def add(source, module=None, explicit=None):
        source = Path(source).resolve()
        assert source.is_file() and source.is_relative_to(ROOT)
        key = relative(source)
        row = records.setdefault(key, dict(path=key, modules=[], explicit=[]))
        if module is not None:
            row['modules'].append(module)
        if explicit is not None:
            row['explicit'].append(explicit)

    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        source = Path(filename).resolve()
        if not (source.is_relative_to(WORK) or
                source.is_relative_to(ROOT/'pro1_controller_bundle')):
            continue
        if source.suffix == '.pyc':
            source = Path(importlib.util.source_from_cache(str(source))).resolve()
        add(source, module=name)
    for source, role in ((HERE/'gen_dqi.py','generator_entrypoint'),
                         (HERE/'build_candidate.py','builder_entrypoint'),
                         (WORK/'runtime/guard.py','external_memory_guard')):
        add(source, explicit=role)
    engine = Path(sys.modules['kickmix'].__file__).resolve()
    assert digest(engine) == ENGINE_SHA
    add(engine, explicit='original_supplied_native_engine')
    for key, row in records.items():
        source = checked_path(key)
        row.update(bytes=source.stat().st_size, sha256=digest(source),
                   modules=sorted(set(row['modules'])), explicit=sorted(set(row['explicit'])))
    value = dict(format='DQI_POST_C5_LOADED_SOURCE_BINDING_V3',
                 status='CAPTURED_NEW_CANDIDATE_SOURCE_BINDING',
                 files=[records[key] for key in sorted(records)], file_count=len(records),
                 source_map_sha256=canonical_digest(records),
                 python=sys.version, executable=sys.executable,
                 entrypoint_audit=entrypoint_audit(),
                 runtime_bindings=pipeline.runtime_bindings(),
                 finish_geometry_binding=pipeline.finish_geometry_binding(),
                 accepted_C5_and_frozen_sources=accepted_after,
                 scopes=['New runtime bindings are explicit and source-hashed.',
                         'The66 accepted C5 sources and14 frozen census dependencies remain byte-identical.',
                         'All84 files in the passed v1 engineering inventory remain byte-identical.',
                         'All86 files in the v2 A/B inventory and the nine v2 source files remain byte-identical.',
                         'Both permanent deferred-flag components are bound to their full native PASS receipts.',
                         'The actual finish and scan use the same hash-bound public M.',
                         'This is neither a source-census PASS nor an official verifier or new population certificate.'])
    atomic_json(path, value)
    return dict(path=str(Path(path).resolve()), sha256=digest(path), files=len(records),
                source_map_sha256=value['source_map_sha256'], status=value['status'])
