#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Inventory the actual builder process without modifying any circuit emitter.

Call write_inventory after emission and before writing the build report.
--audit-only performs the source/argument audit without importing Kickmix.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import tempfile


FORMAT = 'dqi-loaded-source-inventory-v1'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        temporary = None
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _calls(tree, name):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
            ((isinstance(n.func, ast.Attribute) and n.func.attr == name) or
             (isinstance(n.func, ast.Name) and n.func.id == name))]


def _options(tree):
    result = {}
    for call in _calls(tree, 'add_argument'):
        flags = [ast.literal_eval(value) for value in call.args]
        if not flags or any(not isinstance(flag, str) or not flag.startswith('--')
                            for flag in flags):
            raise ValueError('Unexpected positional or nonliteral argument declaration')
        for flag in flags:
            if flag in result:
                raise ValueError('Repeated argument declaration: '+flag)
            result[flag] = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}
    return result


def audit_entrypoints(workspace):
    """Strict audit of this production wrapper and its fixed builder contract."""
    workspace = Path(workspace).resolve()
    paths = {'production_wrapper': workspace/'controller_work/gen_dqi.py',
             'builder': workspace/'controller_work/night_c27/build_candidate.py'}
    trees, sources, findings, files = {}, {}, [], {}
    for role, path in paths.items():
        raw = path.read_bytes()
        sources[role] = raw.decode('utf-8')
        trees[role] = ast.parse(sources[role], filename=str(path))
        files[role] = {'path': str(path.relative_to(workspace)),
                       'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        for text in ('Copyright 2026 Syed Asad Ali', 'Apache-2.0', 'Opus and Astra'):
            if text not in sources[role][:1000]:
                findings.append(role+': missing header '+text)
    wrapper, builder = trees['production_wrapper'], trees['builder']
    wrapper_options, builder_options = _options(wrapper), _options(builder)
    expected_wrapper = {'--output', '--log-directory', '--rss-soft', '--available-reserve'}
    expected_builder = {'--output', '--log-directory', '--engineering-scan-positions',
                        '--conditional-flag-phases'}
    if set(wrapper_options) != expected_wrapper:
        findings.append('Production argument surface differs from the four allowed output/guard options')
    if set(builder_options) != expected_builder:
        findings.append('Builder argument surface differs from the audited fixed set')
    if builder_options.get('--engineering-scan-positions', {}).get('default') != '4095':
        findings.append('Builder full-scan default is not literal 4095')
    for role, tree in trees.items():
        if len(_calls(tree, 'parse_args')) != 1 or _calls(tree, 'parse_known_args'):
            findings.append(role+': unknown arguments are not rejected by one parse_args call')
        for forbidden in ('getenv', 'from_file', 'read_bytes', 'read_text', 'exec', 'eval'):
            if _calls(tree, forbidden):
                findings.append(role+': unexpected dynamic/input call '+forbidden)
        if any(isinstance(n, ast.Attribute) and n.attr == 'environ' for n in ast.walk(tree)):
            findings.append(role+': unexpected environment-driven selector')
    commands = [n.value for n in ast.walk(wrapper) if isinstance(n, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == 'command' for t in n.targets)]
    command = commands[0] if len(commands) == 1 else None
    if not isinstance(command, ast.List) or any(isinstance(n, ast.Starred) for n in command.elts):
        findings.append('Production child command is not one fixed non-expanded list')
        constants = []
    else:
        constants = [n.value for n in ast.walk(command) if isinstance(n, ast.Constant)
                     and isinstance(n.value, str)]
        if constants.count('--conditional-flag-phases') != 1:
            findings.append('Production does not select exactly one conditional-flag option')
        if 'runtime/guard.py' not in constants or 'night_c27/build_candidate.py' not in constants:
            findings.append('Production command does not name the supplied guard and fixed builder')
        allowed_options = {'--log', '--stdout', '--rss-soft', '--reserve', '--',
                           '--output', '--log-directory', '--conditional-flag-phases'}
        if {x for x in constants if x.startswith('--')} != allowed_options:
            findings.append('Production forwards an unexpected child option')
    runs = _calls(wrapper, 'run')
    if len(runs) != 1 or not runs[0].args or not isinstance(runs[0].args[0], ast.Name) or runs[0].args[0].id != 'command':
        findings.append('Production does not invoke exactly its fixed command list')
    emits = [n for n in _calls(builder, 'emit') if isinstance(n.func, ast.Attribute)
             and isinstance(n.func.value, ast.Name) and n.func.value.id == 'Pipeline']
    if len(emits) != 1:
        findings.append('Expected one fixed Pipeline.emit call')
    else:
        kwargs = {kw.arg: ast.unparse(kw.value) for kw in emits[0].keywords}
        if kwargs.get('j_min') != '15' or kwargs.get('scan_positions') != 'a.engineering_scan_positions':
            findings.append('Builder does not select literal j_min=15 and its audited scan extent')
    return {'status': 'PASS_ENTRYPOINT_AST_AUDIT' if not findings else 'FAIL_ENTRYPOINT_AST_AUDIT',
            'files': files, 'wrapper_options': wrapper_options, 'builder_options': builder_options,
            'production_full_scan_positions': 4095, 'production_j_min': 15,
            'production_conditional_flag_phases': True,
            'profile_terminal_contact_salt_arguments': [], 'findings': findings,
            'scope': 'Exact argument and call-site audit, not a proof of all downstream source semantics.'}


def _local_path(path, roots):
    return any(path.is_relative_to(root) for root in roots)


def inventory_loaded_sources(workspace):
    workspace = Path(workspace).resolve()
    work, bundle = workspace/'controller_work', workspace/'pro1_controller_bundle'
    audit = audit_entrypoints(workspace)
    if audit['findings']:
        raise ValueError('Entrypoint audit failed: '+ '; '.join(audit['findings']))
    kickmix = sys.modules.get('kickmix')
    kickmix_path = Path(getattr(kickmix, '__file__', '')).resolve()
    if not kickmix_path.is_file() or not kickmix_path.is_relative_to(bundle/'1_task/official'):
        raise ValueError('Loaded Kickmix is absent or is not the supplied bundle runtime')
    records = {}

    def add(path, *, module=None, explicit=None, observed=None):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError('Inventoried source is missing: '+str(path))
        record = records.setdefault(path, {'path': str(path.relative_to(workspace)),
                                           'loaded_module_names': [], 'explicit_roles': [],
                                           'observed_module_paths': []})
        if module is not None:
            record['loaded_module_names'].append(module)
        if explicit is not None:
            record['explicit_roles'].append(explicit)
        if observed is not None:
            record['observed_module_paths'].append(str(observed))

    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if not _local_path(path, (work, bundle)):
            continue
        source = path
        if path.suffix == '.pyc':
            try:
                candidate = Path(importlib.util.source_from_cache(str(path)))
            except ValueError:
                candidate = path.with_suffix('.py')
            if candidate.is_file():
                source = candidate.resolve()
        add(source, module=name, observed=path)
    for relative, role in (('controller_work/gen_dqi.py', 'production_wrapper'),
                           ('controller_work/night_c27/build_candidate.py', 'builder'),
                           ('controller_work/runtime/guard.py', 'memory_guard')):
        add(workspace/relative, explicit=role)
    add(kickmix_path, explicit='supplied_native_runtime')
    files = []
    for path, record in sorted(records.items(), key=lambda item: str(item[0])):
        record.update(bytes=path.stat().st_size, sha256=digest(path))
        for key in ('loaded_module_names', 'explicit_roles', 'observed_module_paths'):
            record[key] = sorted(set(record[key]))
        if path.suffix == '.py':
            header = path.read_text(encoding='utf-8')[:1500]
            record['header'] = {'apache_2_0': 'Apache-2.0' in header,
                                'syed_asad_ali': 'Syed Asad Ali' in header,
                                'opus_credit': 'Opus' in header,
                                'astra_credit': 'Astra' in header}
        record['origin'] = ('supplied_bundle' if path.is_relative_to(bundle) else
                            'restored_integrator_source' if path.is_relative_to(work/'work/round2') else
                            'clean_room_worktree')
        files.append(record)
    bindings = {}
    for name in ('fixed_pipeline', 'raw_query_extractor'):
        module = sys.modules.get(name)
        tail = getattr(module, 'Tail', None)
        bindings[name+'.Tail'] = getattr(tail, '__name__', None)
    return {'format': FORMAT, 'status': 'CAPTURED_LOADED_SOURCE_INVENTORY',
            'copyright': 'Copyright 2026 Syed Asad Ali', 'license': 'Apache-2.0',
            'credits': ['Opus', 'Astra'],
            'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'workspace': str(workspace), 'python': sys.version, 'executable': sys.executable,
            'platform': platform.platform(), 'files': files, 'file_count': len(files),
            'supplied_kickmix_path': str(kickmix_path.relative_to(workspace)),
            'entrypoint_audit': audit, 'observed_runtime_bindings': bindings,
            'scope': ['All currently loaded local module files under the worktree and supplied bundle.',
                      'Parent wrapper and memory guard are explicit entries, not claimed child imports.',
                      'Loaded imports are not an execution-coverage or originality proof.',
                      'Existing source license/credit headers are recorded without rewriting them.',
                      'This inventory does not read a precompiled circuit or accept an input profile or salt.']}


def write_inventory(path, *, workspace):
    value = inventory_loaded_sources(workspace)
    atomic_json(path, value)
    return {'path': str(Path(path).resolve()), 'sha256': digest(path),
            'files': value['file_count'], 'status': value['status'],
            'entrypoint_audit': value['entrypoint_audit']['status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit-only', action='store_true', required=True)
    args = parser.parse_args()
    report = audit_entrypoints(args.workspace)
    atomic_json(args.output, report)
    print(json.dumps({'status': report['status'], 'sha256': digest(args.output),
                      'findings': report['findings']}))
    return 0 if not report['findings'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
