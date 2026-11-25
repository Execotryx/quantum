# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Ten component cases derived from five exact existing physical records.

No physical case is generated or resampled. Three existing cases are outside
the complete decoder only because their weights are below15; their full35
padded locators satisfy every preimage-domain condition. That distinction is
preserved explicitly in the output rather than relabeling those inputs.
"""
from __future__ import annotations

from collections import Counter
import importlib.util
import json
import sys

import variant_support as Support

INPUT = Support.HERE/'EXISTING_PROFILE_SUPPLEMENT.json'
INPUT_SHA = '58303e050c3caa104bf5538ba76fd159cfb3b054addbfc5a02f343b0d1edd3dc'
SOURCE = Support.WORK/'night_c27/arithmetic/panel_audit/fixed-prepared/cases.json'
SOURCE_SHA = 'abcd3a243eae059312a3d39b5fce19be75e0d692beec20cbd5197d30588932a7'
REFERENCE = Support.WORK/'night_c27/census/reference.py'
REFERENCE_SHA = 'a43a7dbf3ef0cb02f8660067a0067c603cf39fe7a552584c3fc9bc228f501aa6'
RHS_SOURCE = Support.WORK/'after_c5/converter_width/runs/full/fixtures.json'
RHS_SHA = '6e023eb39758c15cc5e3835bc6bcdb0f8ad08c3ec15185d2c970dfbb201fac73'
INDICES = (3205, 3320, 3605, 5894, 6385)


def original_records():
    """Stream only as far as the last fixed index; keep at most one record."""
    decoder = json.JSONDecoder()
    result = {}
    with SOURCE.open() as stream:
        buffer = stream.read(4096)
        marker = '"cases": ['
        assert marker in buffer
        buffer = buffer[buffer.index(marker)+len(marker):]
        for index in range(max(INDICES)+1):
            buffer = buffer.lstrip()
            if buffer.startswith(','):
                buffer = buffer[1:].lstrip()
            while True:
                try:
                    row, end = decoder.raw_decode(buffer)
                    break
                except json.JSONDecodeError:
                    extra = stream.read(65536)
                    assert extra
                    buffer += extra
                    assert len(buffer) < 1000000, 'unexpected single-record size'
            buffer = buffer[end:]
            if index in INDICES:
                result[index] = row
    assert tuple(result) == INDICES
    return result


def fixtures(independent_preimage_reference):
    for path, wanted in ((INPUT, INPUT_SHA), (SOURCE, SOURCE_SHA),
                         (REFERENCE, REFERENCE_SHA), (RHS_SOURCE, RHS_SHA)):
        assert Support.digest(path) == wanted, path
    data = json.loads(INPUT.read_text())
    assert data['format'] == 'DQI_TRANSPOSE14_EXISTING_PROFILE_SUPPLEMENT_V1'
    assert data['new_population_draws'] == data['new_physical_inputs'] == data['native_runs'] == 0
    assert data['source_sha256'] == SOURCE_SHA and data['reference_sha256'] == REFERENCE_SHA
    assert data['rhs_source_sha256'] == RHS_SHA
    assert data['source_path'] == str(SOURCE.relative_to(Support.ROOT))
    assert data['reference_path'] == str(REFERENCE.relative_to(Support.ROOT))
    assert data['rhs_source_path'] == str(RHS_SOURCE.relative_to(Support.ROOT))
    assert tuple(row['original_index'] for row in data['source_records']) == INDICES
    originals = original_records()
    rhs_bank = json.loads(RHS_SOURCE.read_text())
    spec = importlib.util.spec_from_file_location('transpose14_unchanged_classical_reference', REFERENCE)
    field = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = field
    spec.loader.exec_module(field)
    assert not any(name in field.__dict__ for name in ('kickmix', 'numpy', 'random'))
    result = []
    for saved in data['source_records']:
        original = originals[saved['original_index']]
        assert original == saved['original_case']
        exact = field.classify(original['roots'], original['values'], include_polynomials=True)
        assert all(exact[name] == value for name, value in original['classification']['exact'].items())
        assert exact['half']['admitted'] is True and exact['half']['reason_mask'] == 0
        assert exact['finite']['bad'] is False
        assert saved['D'] == exact['padded_locator']
        assert len(saved['D']) == 36 and saved['D'][-1] == 1
        assert saved['O'] == rhs_bank[saved['rhs_from_original256_index']]['O']
        assert sum(bool(value) for value in saved['O']) >= 30
        other_row = rhs_bank[saved['gauge0_other_from_original256_index']]
        assert other_row['gauge_flag'] == 0 and other_row['gauge_other'] != 0
        assert saved['gauge0_other'] == other_row['gauge_other']
        whole = original['classification']['admitted']
        assert saved['whole_decoder_admitted'] == whole
        assert saved['whole_decoder_exclusions'] == original['classification']['reasons']
        assert (whole and saved['whole_decoder_exclusions'] == []) or (
            not whole and saved['whole_decoder_exclusions'] == ['physical_weight_below_public_cutoff'])
        mode = ''.join(str(int(n in exact['half']['drop2_starts'])) for n in (14, 13, 12))
        assert mode == saved['mode'] and mode in ('100', '010', '001')
        Ref = independent_preimage_reference
        assert Ref.admitted(saved['D'])
        assert Ref.profile(saved['D']) == exact['half']['degrees']
        expected = Ref.full_preimage(saved['D'], saved['O'])
        for flag in (0, 1):
            result.append(dict(
                D=saved['D'], O=saved['O'], expected=expected,
                half_profile=exact['half']['degrees'],
                gauge_flag=flag, gauge_other=0 if flag else saved['gauge0_other'],
                forced_top_gap=17 in exact['half']['drop2_starts'],
                source_group='existing_profile_component_supplement',
                source_case_id=original['case_id'], source_label=original['label'],
                source_original_index=saved['original_index'], physical_weight=original['weight'],
                half_core_admitted=True, whole_decoder_admitted=whole,
                whole_decoder_exclusions=saved['whole_decoder_exclusions'], window14_mode=mode))
    assert len(result) == 10
    assert Counter(row['window14_mode'] for row in result) == {'100': 2, '010': 4, '001': 4}
    assert Counter(row['whole_decoder_admitted'] for row in result) == {False: 6, True: 4}
    for path, wanted in ((INPUT, INPUT_SHA), (SOURCE, SOURCE_SHA),
                         (REFERENCE, REFERENCE_SHA), (RHS_SOURCE, RHS_SHA)):
        assert Support.digest(path) == wanted, path
    return result, dict(
        path=str(INPUT.relative_to(Support.ROOT)), sha256=INPUT_SHA,
        source_path=str(SOURCE.relative_to(Support.ROOT)), source_sha256=SOURCE_SHA,
        classical_reference_path=str(REFERENCE.relative_to(Support.ROOT)),
        classical_reference_sha256=REFERENCE_SHA,
        original_indices=list(INDICES), original_physical_records=5,
        component_cases=10, gauges=[0, 1],
        modes=dict(Counter(row['window14_mode'] for row in result)),
        whole_decoder_admitted_cases=4, cutoff_only_excluded_cases=6,
        all_preimage_component_admitted=True, new_population_draws=0,
        new_physical_inputs=0,
        qualification='Three saved physical inputs have weight9/10 and remain outside cutoff15; only their preimage-domain padded locators are tested here.')
