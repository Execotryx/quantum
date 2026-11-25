#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-only deterministic physical fixture with raw third residue zero.

No sampler or population draw is used. Keep one old admitted support, vary
one magnitude through a fixed bounded list, and solve its last two nonzero
magnitudes exactly from the two base-field equations for the zero residue.
The unchanged complete classifier and physical boundary oracle must accept
the constructed case before any fixture package is written.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]
ROOT = WORK.parent
PANEL = WORK/'night_c27/arithmetic/panel_audit'
SOURCE = PANEL/'prepared/cases.json'
PINS = {
    'controller_work/night_c27/arithmetic/panel_audit/prepared/cases.json': 'eb9216d25bd69f17179533932f0ec6a8704860a366117bd370b6eec35495e339',
    'controller_work/night_c27/arithmetic/panel_audit/prepare_panels.py': '4007bd123f1eb77431acb32c6811d838e30f4455b6f87c537413955533962fa7',
    'controller_work/night_c27/arithmetic/panel_audit/physical_boundary_oracle.py': 'b2d7871501afdb528820c78989e408098ca441153fa16f98d4b5f9697810db99',
    'controller_work/night_c27/census/reference.py': 'a43a7dbf3ef0cb02f8660067a0067c603cf39fe7a552584c3fc9bc228f501aa6',
    'controller_work/after_c5/extractor_width/direct_carry_scalar_screen.py': '0dd91ca47acab0a466e27e6374f9751e739e0c06f7b973b2d4aa34df034ceb28',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic(path, value):
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--maximum-free-values', type=int, default=64)
    args = parser.parse_args()
    assert __debug__ and 1 <= args.maximum_free_values <= 4095
    assert not args.output.exists(), 'Use a new fixture directory'
    for name, wanted in PINS.items():
        assert digest(ROOT/name) == wanted, name
    sys.path.insert(0, str(PANEL))
    import prepare_panels as Panels
    import physical_boundary_oracle as Oracle
    import boundary_scale_first3 as Adapter
    Ref = Panels.Ref
    package = json.loads(SOURCE.read_text())
    assert package['format'] == 'C27_PHYSICAL_PANEL_V1' and package['j_min'] == 15
    base_index, original = next((index, row) for index, row in enumerate(package['cases'])
        if row['weight'] >= 15 and row['classification']['admitted'])
    roots = list(original['roots'])
    assert len(roots) >= 15 and len(set(roots)) == len(roots)
    coefficients = []
    for root in roots:
        weight = root
        at = Ref.mul(root, root) ^ root
        for constant in Ref.KAPPAS:
            weight = Ref.mul(weight, at ^ constant)
        # At the public third place alpha=theta+4; every root is in the base field.
        coefficients.append(Adapter.kscale(Adapter.kinverse((root ^ 4) | (1 << 12)), weight))
    left, right = coefficients[-2:]
    la, lb, ra, rb = left & 4095, left >> 12, right & 4095, right >> 12
    determinant = Ref.mul(la, rb) ^ Ref.mul(lb, ra)
    assert determinant, 'distinct physical roots give independent residue columns'
    inverse_determinant = Ref.INV[determinant]
    attempts, found = [], None
    for free in range(1, args.maximum_free_values+1):
        values = list(original['values'])
        values[0] = free
        target = 0
        for coefficient, value in zip(coefficients[:-2], values[:-2]):
            target ^= Adapter.kscale(coefficient, value)
        ta, tb = target & 4095, target >> 12
        values[-2] = Ref.mul(Ref.mul(ta, rb) ^ Ref.mul(tb, ra), inverse_determinant)
        values[-1] = Ref.mul(Ref.mul(la, tb) ^ Ref.mul(lb, ta), inverse_determinant)
        if not values[-2] or not values[-1]:
            attempts.append(dict(free_value=free, status='zero_solved_magnitude'))
            continue
        check = 0
        for coefficient, value in zip(coefficients, values):
            check ^= Adapter.kscale(coefficient, value)
        assert check == 0
        classification = Ref.classify(roots, values)
        attempts.append(dict(free_value=free, reason_mask=classification['reason_mask'],
                             admitted=not classification['union']['15']))
        if classification['union']['15']:
            continue
        old = Oracle.boundary(roots, values, j_min=15)
        assert old['raw_queries'][2] == 0
        new = Adapter.rescale_boundary(old)
        assert new['third_chart']['raw_zero'] and new['third_chart']['middle'] == 0
        assert new['third_chart']['queried_numerator'] and new['third_chart']['queried_denominator']
        found = values, classification, old, new
        break
    if found is None:
        raise RuntimeError('No admitted nonzero-magnitude solution in the bounded deterministic list')
    values, classification, old, new = found
    positions = [Ref.LOG[root] for root in roots]
    row = dict(label='third_raw_residue_zero_exact_two_magnitude_solve',
               positions=positions, roots=roots, values=values, weight=len(roots),
               mask_mode='random', syndromes=Panels.moments(positions, values),
               certificate=dict(raw_query_index=2, exact_raw_query_value=0,
                   fixed_support_source_case_id=original['case_id'], fixed_support_source_index=base_index,
                   solved_magnitude_indices=[len(values)-2, len(values)-1],
                   free_magnitude_index=0, free_magnitude_value=values[0],
                   determinant=determinant, classification=classification,
                   no_population_draws=True), C5_boundary=old, candidate_boundary=new)
    Panels.validate(row)
    for name, wanted in PINS.items():
        assert digest(ROOT/name) == wanted, name
    bindings = dict(PINS)
    for path in (Path(__file__), Path(Adapter.__file__)):
        bindings[str(path.resolve().relative_to(ROOT))] = digest(path)
    args.output.mkdir(parents=True, exist_ok=False)
    body = dict(format='C27_EXTRA_PHYSICAL_FIXTURES_V1',
                panel='first3_raw_residue_zero_exact_linear_solve',
                classifier_sha256=digest(Ref.__file__), cases=[row])
    atomic(args.output/'cases.json', body)
    report = dict(status='PREPARED_ADMITTED_PHYSICAL_THIRD_RAW_ZERO_FIXTURE_NOT_NATIVE',
                  cases=1, attempts=attempts, new_population_draws=0,
                  unchanged_support=True, actual_nonzero_magnitudes=True,
                  unchanged_complete_classifier_admitted=True,
                  exact_C5_raw_query_zero=True, new_gauge=new['gauge'],
                  source_bindings=bindings, prepared_cases_sha256=digest(args.output/'cases.json'),
                  native_checked=False, population_claim=False,
                  scope='One deterministic exact construction; no probability estimate or official run')
    atomic(args.output/'report.json', report)
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
