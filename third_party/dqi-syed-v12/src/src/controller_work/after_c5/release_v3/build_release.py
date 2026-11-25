#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed release bootstrap with three exactly derived text-only modules.

The source derivation checker is pure stdlib and safe to import for audit.
Only main() imports the supplied native builder. It never reads an old KMB.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V3 = HERE.parent/'integration_v3'
MANIFEST_SHA = '9ed1309dcfd4f777ca5bc930d6e0473cf54341fb6ede9da439a34070e86698c6'
REFERENCE_INVENTORY_SHA = '482aca96da9bddd86611570f1fd8385612d1136ea43854e6c46072fd7f733ac6'
REFERENCE_SOURCE_MAP = '6bcd9bbcd80c28e91938ae1cf59baab84a67e517196f923407d00bf97e827918'
EXPECTED_CIRCUIT_SHA = 'ed5a3014c1eaeb1855fc820f4f1076d1f70fe69edf5632482c62fb24f2b87c7a'
MODULES = ('window_tensor_shared', 'local_flag_window', 'direct_carry_first2')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def checked_path(name):
    path = Path(name)
    assert not path.is_absolute() and path.as_posix() == name and '..' not in path.parts
    result = (ROOT/path).resolve()
    assert result.is_relative_to(ROOT) and result.is_file()
    return result


def ast_form(data, row, version):
    tree = ast.parse(data)
    assert tree.body and isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str)
    docstring = tree.body[0].value.value
    tree.body = tree.body[1:]
    if row['kind'] == 'module_docstring':
        assert row[version+'_fragment'] in docstring
    else:
        assert row['kind'] == 'stage_label'
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == row['class_name']]
        assert len(classes) == 1 and row['class_name'] == 'Step'
        methods = [node for node in classes[0].body if isinstance(node, ast.FunctionDef)
                   and node.name == row['method_name']]
        assert len(methods) == 1 and row['method_name'] == 'gauge_shared_source'
        literal = row[version+'_literal_value']
        assert row[version+'_fragment'] == repr(literal)
        candidates = [node for node in ast.walk(methods[0]) if isinstance(node, ast.Call)
                      and isinstance(node.func, ast.Attribute)
                      and node.func.attr == row['call_attribute']
                      and isinstance(node.func.value, ast.Name)
                      and node.func.value.id == row['receiver_name']
                      and len(node.args) == 1 and not node.keywords
                      and isinstance(node.args[0], ast.Constant)
                      and node.args[0].value == literal]
        assert len(candidates) == 1
        assert row['receiver_name'] == 'carrier' and row['call_attribute'] == 'unpark'
        occurrences = [node for node in ast.walk(tree)
                       if isinstance(node, ast.Constant) and node.value == literal]
        assert occurrences == [candidates[0].args[0]]
        candidates[0].args[0].value = 'REVIEWED_NONSEMANTIC_STAGE_LABEL'
    # Explicit empty fields keep the preparation and Python3.13 serializers
    # identical; omitting them would change only the recorded AST hash text.
    return ast.dump(tree, include_attributes=False, show_empty=True), docstring


def validate_normalization():
    manifest_path = HERE/'NORMALIZATION.json'
    assert digest(manifest_path) == MANIFEST_SHA
    manifest = json.loads(manifest_path.read_text())
    assert manifest['format'] == 'DQI_V3_NONSEMANTIC_SOURCE_NORMALIZATION_V1'
    assert manifest['original_files_edited'] is False
    assert manifest['normalized_module_count'] == len(manifest['changes']) == 3
    assert tuple(row['module'] for row in manifest['changes']) == MODULES
    verified = []
    for row in manifest['changes']:
        source, target = checked_path(row['source']), checked_path(row['target'])
        assert target == HERE/'normalized'/(row['module']+'.py')
        assert not source.is_relative_to(HERE) and source.suffix == '.py'
        old, new = source.read_bytes(), target.read_bytes()
        assert len(old) == row['old_bytes'] and len(new) == row['new_bytes']
        assert hashlib.sha256(old).hexdigest() == row['old_sha256']
        assert hashlib.sha256(new).hexdigest() == row['new_sha256']
        fragment, replacement = row['old_fragment'].encode(), row['new_fragment'].encode()
        assert row['fragment_occurrences'] == old.count(fragment) == 1
        assert new == old.replace(fragment, replacement, 1)
        before, old_doc = ast_form(old, row, 'old')
        after, new_doc = ast_form(new, row, 'new')
        assert before == after
        assert hashlib.sha256(before.encode()).hexdigest() == row['normalized_ast_sha256']
        if row['kind'] == 'stage_label':
            assert old_doc == new_doc
        verified.append(dict(module=row['module'], source=row['source'], target=row['target'],
                             old_sha256=row['old_sha256'], new_sha256=row['new_sha256'],
                             exact_once_only_replacement=True,
                             narrow_AST_equivalence=True,
                             normalized_ast_sha256=row['normalized_ast_sha256']))
    return dict(status='PASS_EXACT_NONSEMANTIC_SOURCE_DERIVATION_ONLY',
                manifest=dict(path=relative(manifest_path), sha256=MANIFEST_SHA),
                changes=verified, original_files_edited=False,
                no_native_result_inferred=True)


def reference_inventory():
    path = V3/'runs/a/build/source-inventory.json'
    assert digest(path) == REFERENCE_INVENTORY_SHA
    inventory = json.loads(path.read_text())
    assert inventory['format'] == 'DQI_POST_C5_LOADED_SOURCE_BINDING_V3'
    assert inventory['status'] == 'CAPTURED_NEW_CANDIDATE_SOURCE_BINDING'
    records = {row['path']: row for row in inventory['files']}
    assert len(records) == len(inventory['files']) == inventory['file_count'] == 88
    assert canonical_digest(records) == inventory['source_map_sha256'] == REFERENCE_SOURCE_MAP
    return inventory, records


def validate_runtime_inventory(path):
    """Bind observed imports to the exact old-map substitution, not equality."""
    derivation = validate_normalization()
    reference, expected = reference_inventory()
    manifest = json.loads((HERE/'NORMALIZATION.json').read_text())
    for row in manifest['changes']:
        prior = expected.pop(row['source'])
        assert prior['sha256'] == row['old_sha256'] and prior['bytes'] == row['old_bytes']
        assert prior['modules'] == [row['module']] and prior['explicit'] == []
        changed = dict(prior, path=row['target'], sha256=row['new_sha256'], bytes=row['new_bytes'])
        assert changed['path'] not in expected
        expected[changed['path']] = changed
    builder_path = relative(V3/'build_candidate.py')
    assert expected[builder_path]['modules'] == ['__main__']
    expected[builder_path] = dict(expected[builder_path], modules=['build_candidate'])
    own_path = relative(HERE/'build_release.py')
    assert own_path not in expected
    expected[own_path] = dict(path=own_path, modules=['__main__'], explicit=[],
                              bytes=(HERE/'build_release.py').stat().st_size,
                              sha256=digest(HERE/'build_release.py'))
    inventory = json.loads(Path(path).read_text())
    assert inventory['format'] == 'DQI_POST_C5_LOADED_SOURCE_BINDING_V3'
    assert inventory['status'] == 'CAPTURED_NEW_CANDIDATE_SOURCE_BINDING'
    observed = {row['path']: row for row in inventory['files']}
    assert inventory['file_count'] == len(inventory['files']) == len(observed) == len(expected) == 89
    assert observed == expected, ('Unexpected imported-source change', sorted(set(observed)^set(expected)))
    assert inventory['source_map_sha256'] == canonical_digest(observed)
    assert inventory['source_map_sha256'] != REFERENCE_SOURCE_MAP
    assert inventory['runtime_bindings']['options'] == {
        'first_two_charts': True, 'nested_norm': True,
        'finish_seam': True, 'infinity3_finish': True}
    for key in ('accepted_C5_and_frozen_sources', 'entrypoint_audit',
                'runtime_bindings', 'finish_geometry_binding'):
        assert inventory[key] == reference[key], ('Unexpected binding change', key)
    for row in observed.values():
        source = checked_path(row['path'])
        assert source.stat().st_size == row['bytes'] and digest(source) == row['sha256']
    return dict(status='PASS_OBSERVED_NORMALIZED_RUNTIME_SOURCE_SUBSTITUTION',
                inventory_sha256=digest(path), observed_child_files=89,
                observed_child_python_files=88,
                source_map_sha256=inventory['source_map_sha256'],
                original_v3_source_map_sha256=REFERENCE_SOURCE_MAP,
                original_source_map_equality_claimed=False,
                normalized_modules_actually_observed=True,
                added_child_module=own_path, parent_wrapper_not_in_child_inventory=True,
                expected_stage_label_metadata_change=True,
                derivation=derivation)


def load_fixed_runtime():
    """Load the exact production builder/modules; emit no circuit here."""
    assert sys.version_info[:2] == (3, 13)
    derivation = validate_normalization()
    # Public, fixed import overlay. No environment variable or input profile
    # selects these files, and all original preservation gates remain intact.
    sys.path.insert(0, str(V3))
    import integration_paths
    assert Path(integration_paths.__file__).resolve() == V3/'integration_paths.py'
    # integration_paths prepends its other directories and skips an already
    # present V3 directory. Restore builder priority after that fixed setup.
    sys.path.insert(0, str(V3))
    import build_candidate
    assert Path(build_candidate.__file__).resolve() == V3/'build_candidate.py', (
        'Unexpected builder import', build_candidate.__file__, str(V3/'build_candidate.py'))
    before = build_candidate.verify_accepted_sources()
    reference, _ = reference_inventory()
    assert before == reference['accepted_C5_and_frozen_sources']
    assert all(name not in sys.modules for name in MODULES)
    sys.path.insert(0, str(HERE/'normalized'))
    import window_tensor_shared
    import local_flag_window
    import direct_carry_first2
    loaded = (window_tensor_shared, local_flag_window, direct_carry_first2)
    for module, name in zip(loaded, MODULES):
        assert module.__name__ == name
        assert Path(module.__file__).resolve() == HERE/'normalized'/(name+'.py')
    return build_candidate, loaded, derivation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--log-directory', type=Path, required=True)
    args = parser.parse_args()
    build_candidate, _loaded, derivation = load_fixed_runtime()
    previous_argv = sys.argv
    sys.argv = [str(V3/'build_candidate.py'), '--output', str(args.output.resolve()),
                '--log-directory', str(args.log_directory.resolve()),
                '--first-two-charts', '--nested-norm', '--finish-seam', '--infinity3-finish']
    try:
        build_candidate.main()
    finally:
        sys.argv = previous_argv
    assert validate_normalization() == derivation
    logs = args.log_directory.resolve()
    proof = validate_runtime_inventory(logs/'source-inventory.json')
    build = json.loads((logs/'build.json').read_text())
    assert build['full_DQI_scan'] is True and build['sha256'] == EXPECTED_CIRCUIT_SHA
    assert build['contract']['scan']['physical_positions'] == 4095
    assert build['contract']['j_min'] == 15
    proof.update(status='BUILT_CANONICAL_V3_WITH_OBSERVED_NORMALIZED_RUNTIME',
                 circuit_sha256_reported_by_unchanged_builder=build['sha256'],
                 actual_output_hash_rechecked_by_parent=False,
                 official_verifier_run=False)
    temporary = logs/'normalization-runtime.json.tmp'
    temporary.write_text(json.dumps(proof, indent=2, sort_keys=True)+'\n')
    temporary.replace(logs/'normalization-runtime.json')
    print(json.dumps(proof, indent=2), flush=True)


if __name__ == '__main__':
    main()

