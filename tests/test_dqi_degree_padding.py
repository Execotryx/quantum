"""Check coherent degree padding against independent polynomial products."""

from collections.abc import Sequence
from functools import cache
from importlib import import_module
from pathlib import Path
from random import Random
import subprocess
import sys

import numpy as np
import pytest

from qcompile.dqi.decoder import _add, _divide, _multiply, bm_locator, syndrome
from qcompile.dqi.degree_padding import pad_reversed_banks, padding_factors
from qcompile.dqi.field import GF4096
from qcompile.dqi.locator_fraction import blocked_suffix_inplace, projective_continuant
from qcompile.dqi.quotient import _product_range
from qcompile.dqi.scan import degree_padded_chart_xor, degree_padded_residue_scan, derivative_reciprocal, evaluator
from qcompile.dqi.tower import ProjectedFieldProduct
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


FIELD = GF4096()
CHART = tuple(range(16, -1, -1))


def _reverse(poly, degree):
    return (poly + [0] * (degree - len(poly)))[::-1] + [0] * (35 - degree)


def _case(support):
    weight = len(support)
    locator = [1]
    for position in support:
        locator = _multiply(locator, [FIELD.exp[-position % 4095], 1], FIELD)
    omega = evaluator(syndrome(support, FIELD), locator, FIELD) if weight else []
    factor = [1] if weight % 2 else [0, 1]
    for linear, constant in padding_factors()[:(35 - weight) // 2]:
        factor = _multiply(factor, [constant, linear, 1], FIELD)
    modulus = _multiply(locator, factor, FIELD)
    padded_omega = _multiply(omega, factor, FIELD) if omega else []
    return (_reverse(locator[:-1], weight) + _reverse(omega, weight) + [weight],
            _reverse(modulus[:-1], 35) + _reverse(padded_omega, 35) + [weight], support)


def _regular_chart(padded: list[int]) -> bool:
    a = padded[:35][::-1] + [1]
    b = [a[i + 1] if i % 2 == 0 else 0 for i in range(35)]
    for expected in CHART:
        _, remainder = _divide(a, b, FIELD)
        if remainder == [0] or len(remainder) - 1 != 2 * expected:
            return False
        a, b = b, remainder
    return True


def _cases(*, regular_only=False):
    rng = Random(36317)
    rows = []
    for weight in range(36):
        for _ in range(32 if regular_only else 2):
            support = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), weight)}
            case = _case(support)
            if regular_only and not _regular_chart(case[1]):
                continue
            rows.append(case)
            if regular_only:
                break
    return rows


def _phase_cases(guarded: bool):
    cases = _cases(regular_only=True)
    assert [row[0][-1] for row in cases] == list(range(36))
    if guarded:
        rng = Random(36391)
        # Use genuine full-radius syndromes with a nonregular padded chart.
        for i in range(2_048):
            weight = 32 + i % 4
            support = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), weight)}
            case = _case(support)
            if not _regular_chart(case[1]):
                cases.append(case)
            if len(cases) == 40:
                break
        assert len(cases) == 40
    return cases


class _BasisBuilder:
    """Packed value-only gate replay of the emitted reversible pad."""

    def __init__(self, rows, widths: Sequence[int] | None = None):
        self.data = []
        if widths is None:
            widths = [12] * 70 + [6] + [1] * (len(rows[0]) - 71)
        for column, width in zip(zip(*rows, strict=True), widths, strict=True):
            for bit in range(width):
                self.data.append(sum(((word >> bit) & 1) << i for i, word in enumerate(column)))
        self.full = (1 << len(rows)) - 1
        self.charged_ands = 0

    def alloc_qubits(self, size) -> Sequence[int]:
        start = len(self.data)
        self.data.extend([0] * size)
        return range(start, start + size)

    def free(self, wires):
        if isinstance(wires, int):
            wires = (wires,)
        assert all(self.data[i] == 0 for i in wires)

    def flip_if_equal(self, word, value, *, target):
        plane = self.full
        for bit, wire in enumerate(word):
            plane &= self.data[wire] ^ (0 if value >> bit & 1 else self.full)
        self.data[target] ^= plane

    def cx(self, source, target):
        if isinstance(source, int):
            self.data[target] ^= self.data[source]
        else:
            for left, right in zip(source, target, strict=True):
                self.cx(left, right)

    def x(self, target):
        self.data[target] ^= self.full

    def swap(self, left, right):
        if isinstance(left, int):
            self.data[left], self.data[right] = self.data[right], self.data[left]
        else:
            for a, b in zip(left, right, strict=True):
                self.swap(a, b)

    def init_and(self, left, right, target):
        assert self.data[target] == 0
        self.data[target] = self.data[left] & self.data[right]
        self.charged_ands += 1

    def del_and(self, left, right, target):
        assert self.data[target] == self.data[left] & self.data[right]
        self.data[target] = 0


@cache
def _field_columns(scale: int) -> tuple[int, ...]:
    return tuple(FIELD.fixed_map(scale))


class _PhaseBuilder(_BasisBuilder):
    """Replay the padding and phase emitters as packed classical trajectories."""

    def __init__(self, rows, seed: int, widths: Sequence[int] | None = None):
        super().__init__(rows, widths)
        self.shots = len(rows)
        self.phase = 0
        self.controls = [self.full]
        self.rng = Random(seed)
        self.available: list[int] = []
        self.bits: dict[int, int] = {}
        self.first_bit = 0
        self.equality_calls = 0
        self.chart_flags: list[int] = []

    def alloc_qubits(self, size: int):
        reused = self.available[-size:]
        if reused:
            del self.available[-len(reused):]
        return [*reused, *super().alloc_qubits(size - len(reused))]

    def alloc_bits(self, size: int):
        allocated = list(range(self.first_bit - size, self.first_bit))
        self.first_bit -= size
        self.bits.update(dict.fromkeys(allocated, 0))
        return allocated

    def free(self, wires):
        wires = [wires] if isinstance(wires, int) else wires
        for wire in wires:
            if wire < 0:
                assert self.bits.pop(wire) == 0
            else:
                assert self.data[wire] == 0
                self.available.append(wire)

    def x(self, target):
        if isinstance(target, int):
            super().x(target)
        else:
            for wire in target:
                super().x(wire)

    def flip_if_equal(self, word, value, *, target):
        self.equality_calls += 1
        before = self.data[target]
        super().flip_if_equal(word, value, target=target)
        if len(word) == len(CHART):
            self.chart_flags.append(before ^ self.data[target])

    def hmr(self, words, outcomes):
        for wire, bit in zip(words, outcomes, strict=True):
            random_bits = self.rng.getrandbits(self.shots)
            self.phase ^= self.data[wire] & random_bits
            self.data[wire] = 0
            self.bits[bit] = random_bits

    def bit_store(self, bits, value: bool):
        for bit in bits:
            self.bits[bit] = self.full if value else 0

    def push_condition(self, outcome: int):
        self.controls.append(self.controls[-1] & self.bits[outcome])

    def pop_condition(self):
        self.controls.pop()

    def cz(self, left: int, right: int):
        self.phase ^= self.controls[-1] & self.data[left] & self.data[right]

    def ccz(self, flag: int, residue, masks):
        for wire, bit in zip(residue, masks, strict=True):
            self.phase ^= self.data[flag] & self.data[wire] & self.bits[bit]

    def gf2_imul(self, scale: int, *, target, field):
        coefficients = [0] * 12
        for source, column in zip(target, _field_columns(scale), strict=True):
            while column:
                bit = column & -column
                coefficients[bit.bit_length() - 1] ^= self.data[source]
                column ^= bit
        for wire, value in zip(target, coefficients, strict=True):
            self.data[wire] = value

    def gf2_idiv(self, scale: int, *, target, field):
        self.gf2_imul(FIELD.inv(scale), target=target, field=field)


def _field_product(project_root: Path, monkeypatch, tmp_path: Path, *, projected: bool = False):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tensor = tmp_path / "scheme42.txt"
    generator = project_root / "third_party/dqi-scheme42/src/scheme42.py"
    subprocess.run([sys.executable, "-B", str(generator), str(tensor)], check=True)
    # The published text digest uses LF. The generator writes native endings.
    tensor.write_bytes(tensor.read_bytes().replace(b"\r\n", b"\n"))
    return import_module("dqi_quotient").load_field_product(tensor, projected=projected)


def _original_support(support: dict[int, int], reciprocal: bool) -> dict[int, int]:
    if not reciprocal:
        return support
    recovered = {-position % 4095: FIELD.mul(value, FIELD.exp[71 * position % 4095])
                 for position, value in support.items()}
    assert syndrome(recovered, FIELD) == syndrome(support, FIELD)[::-1]
    return recovered


def _blocked_case(series: list[int], steps: int):
    a, b, c, d = [1], [0], [0], [1]
    residual = series
    for _ in range(steps):
        if not residual[0]:
            return None
        inverse = [FIELD.inv(residual[0])]
        for k in range(1, len(residual)):
            value = 0
            for i in range(1, k + 1):
                value ^= FIELD.mul(residual[i], inverse[k - i])
            inverse.append(FIELD.mul(value, inverse[0]))
        q, residual = inverse[:2], inverse[2:]
        a, b, c, d = [0, 0, *b], _add(a, _multiply(b, q, FIELD)), [0, 0, *d], _add(c, _multiply(d, q, FIELD))
    combined = _add(_multiply(d, series, FIELD), b)
    combined += [0] * max(0, len(series) - len(combined))
    assert not any(combined[:2 * steps])
    lead = d[0]
    previous = [FIELD.div(value, lead) for value in c[2:]]
    current = [FIELD.div(value, lead) for value in d[1:]]
    previous += [0] * (steps - len(previous))
    current += [0] * (steps - len(current))
    prefolded = [FIELD.mul(value, lead) for value in combined[2 * steps:len(series)]]
    return [*previous, *current, *prefolded], [*previous, *current, *residual]


def test_reversed_padding_covers_all_value_degrees():
    cases = _cases()
    assert len(cases) == 72
    orig = [row[0] for row in cases]
    padded = [row[1] for row in cases]
    builder = _BasisBuilder(orig)
    size = len(builder.data)
    words = [range(i * 12, (i + 1) * 12) for i in range(70)]
    degree = range(840, 846)
    pad_reversed_banks(builder, words[:35], words[35:], degree)
    assert builder.data[:size] == _BasisBuilder(padded).data
    assert builder.charged_ands == 4_584
    pad_reversed_banks(builder, words[:35], words[35:], degree, adjoint=True)
    assert builder.data[:size] == _BasisBuilder(orig).data
    assert not any(builder.data[size:])


def test_padded_residues_recover_exact_support():
    exponents = -np.arange(4095)
    powers = np.asarray(FIELD.exp)
    logs = np.asarray(FIELD.log)

    def all_evaluations(poly: list[int]):
        values = np.zeros_like(exponents)
        for coefficient in reversed(poly):
            values = np.where(values != 0, powers[(logs[values] + exponents) % 4095], 0) ^ coefficient
        return values

    for _, padded, support in _cases():
        locator = padded[:35][::-1] + [1]
        omega = padded[35:70][::-1]
        product = _multiply(omega, derivative_reciprocal(locator, FIELD), FIELD)
        _, residue = _divide(product, locator, FIELD)
        roots = np.flatnonzero(all_evaluations(locator) == 0)
        assert roots.tolist() == sorted(support)
        recovered = all_evaluations(residue)
        assert {int(j): int(recovered[j]) for j in roots} == support


@pytest.mark.slow
def test_projected_interpolation_xors_dirty_outputs(project_root, monkeypatch, tmp_path):
    multiply, _ = _field_product(project_root, monkeypatch, tmp_path, projected=True)
    rng = Random(36479)
    widths = [12] * 29
    size = sum(widths)
    rows = [[rng.randrange(4096) for _ in widths] for _ in range(12)]
    expected = [row[:18] + [a ^ b for a, b in zip(row[18:], _multiply(row[:7], row[7:18], FIELD)[3:14], strict=True)]
                for row in rows]
    words = [range(i * 12, (i + 1) * 12) for i in range(len(widths))]
    measured = []
    for emit in (multiply, multiply.__call__):
        builder = _PhaseBuilder(rows, 36491, widths)
        _product_range(builder, words[:7], words[7:18], words[18:], 3, emit)
        assert builder.data[:size] == _BasisBuilder(expected, widths).data
        measured.append((builder.charged_ands, len(builder.data) - size))
        _product_range(builder, words[:7], words[7:18], words[18:], 3, emit)
        assert builder.data[:size] == _BasisBuilder(rows, widths).data
        assert not any(builder.data[size:]) and builder.phase == 0 and not builder.bits
    assert measured == [(714, 27), (714, 39)]


@pytest.mark.slow
@pytest.mark.parametrize("degree", [1, 5, 35])
def test_projective_locator_continuant(project_root, monkeypatch, tmp_path, degree):
    multiply, tensor_hash = _field_product(project_root, monkeypatch, tmp_path, projected=True)
    assert isinstance(multiply, ProjectedFieldProduct)
    rng = Random(36527)
    tapes = [[value for _ in range(degree) for value in (rng.randrange(1, 4096), rng.randrange(4096))]
             for _ in range(12)]
    references = []
    for _ in range(24):
        support = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), degree)}
        values = syndrome(support, FIELD)
        locator = bm_locator(values, FIELD)
        omega = evaluator(values, locator, FIELD)
        reference = locator[::-1] + (omega + [0] * (degree - len(omega)))[::-1]
        denominator, numerator = reference[:degree + 1], reference[degree + 1:]
        tape = []
        while numerator != [0]:
            quotient, remainder = _divide(denominator, numerator, FIELD)
            if len(quotient) != 2:
                break
            tape.extend(reversed(quotient))
            denominator, numerator = numerator, remainder
        if len(tape) == 2 * degree:
            tapes.append(tape)
            references.append(reference)
        if len(references) == 12:
            break
    assert len(references) == 12
    widths = [12] * (2 * degree + 1)
    words = [range(i * 12, (i + 1) * 12) for i in range(len(widths))]
    expected_pairs = []
    for tape in tapes:
        denominator, numerator = [1], [0]
        for i in range(len(tape) - 2, -1, -2):
            a, b = tape[i:i + 2]
            next_denominator = _add(_multiply([b, a], denominator, FIELD), numerator)
            numerator, denominator = denominator, next_denominator
        expected_pairs.append([*denominator, *numerator])
    for pair, reference in zip(expected_pairs[-len(references):], references, strict=True):
        assert [FIELD.div(value, pair[-degree - 1]) for value in pair] == reference
    builder = _PhaseBuilder([tape + [0] for tape in tapes], 36529, widths)
    initial = builder.data.copy()
    denominator, numerator = projective_continuant(builder, words[:-1], words[-1], multiply=multiply)
    output = [builder.data[wire] for word in denominator + numerator for wire in word]
    assert output == _BasisBuilder(expected_pairs, widths).data
    size = len(initial)
    assert not any(builder.data[size:]) and builder.phase == 0 and not builder.bits
    forward = builder.charged_ands
    projective_continuant(builder, words[:-1], words[-1], adjoint=True, multiply=multiply)
    assert builder.data[:size] == initial
    assert not any(builder.data[size:]) and builder.phase == 0 and not builder.bits
    assert builder.charged_ands == 2 * forward
    assert len(builder.data) <= size + 33
    write_json(tmp_path / "projective-locator-continuant.json", {
        "scope": "software continuant on a supplied regular quotient tape with an extra unit word",
        "degree": degree, "shots": len(tapes), "syndrome_derived_tapes": len(references), "tensor_sha256": tensor_hash,
        "qubits": len(builder.data), "controlled_products_per_direction": forward,
    })


@pytest.mark.slow
@pytest.mark.parametrize(("degree", "steps"), [(3, 1), (35, 17)])
def test_blocked_locator_suffix(project_root, monkeypatch, tmp_path, degree, steps):
    multiply, tensor_hash = _field_product(project_root, monkeypatch, tmp_path)
    rng = Random(36427)
    cases = []
    for _ in range(24):
        support = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), degree)}
        case = _blocked_case(syndrome(support, FIELD)[:2 * degree], steps)
        if case is not None:
            cases.append(case)
        if len(cases) == 12:
            break
    assert len(cases) == 12
    words = [range(i * 12, (i + 1) * 12) for i in range(2 * degree)]
    widths = [12] * len(words)
    observed = {}
    for adjoint in (False, True):
        builder = _PhaseBuilder([case[int(adjoint)] for case in cases], 36439, widths)
        expected = _BasisBuilder([case[int(not adjoint)] for case in cases], widths).data
        blocked_suffix_inplace(builder, words[2 * steps:], words[:steps], words[steps:2 * steps],
                               adjoint=adjoint, multiply=multiply)
        assert builder.data[:len(expected)] == expected and not any(builder.data[len(expected):])
        assert builder.phase == 0 and not builder.bits
        observed["inverse" if adjoint else "forward"] = {
            "qubits": len(builder.data), "controlled_products": builder.charged_ands,
        }
    write_json(tmp_path / "blocked-locator-suffix.json", {
        "scope": "software suffix transformation with supplied normalized denominator summary and prefolded suffix",
        "degree": degree, "steps": steps, "shots": len(cases), "tensor_sha256": tensor_hash, "observed": observed,
    })


@pytest.mark.slow
def test_chart_decision_without_evaluator(project_root, monkeypatch, tmp_path):
    multiply, tensor_hash = _field_product(project_root, monkeypatch, tmp_path)
    cases = _phase_cases(True)
    target = 846
    initial = [row[0] + [i % 2] for i, row in enumerate(cases)]
    words = [range(i * 12, (i + 1) * 12) for i in range(35)]
    degree = range(840, 846)
    builder = _PhaseBuilder(initial, 36401)
    original = builder.data.copy()
    expected = sum(int(_regular_chart(row[1])) << i for i, row in enumerate(cases))
    degree_padded_chart_xor(builder, words, degree, target, multiply=multiply)
    assert builder.data[target] == original[target] ^ expected
    assert builder.data[:target] == original[:target] and not any(builder.data[target + 1:])
    assert builder.phase == 0 and not builder.bits
    one_probe = {"explicit_products": builder.charged_ands, "equality_calls": builder.equality_calls,
                 "software_allocated_qubits": len(builder.data)}
    degree_padded_chart_xor(builder, words, degree, target, multiply=multiply)
    assert builder.data[:target + 1] == original and not any(builder.data[target + 1:])
    assert builder.phase == 0 and not builder.bits
    assert builder.chart_flags == [expected, expected]
    write_json(tmp_path / "padded-chart-only.json", {
        "scope": "coherent chart XOR from compact locator and live degree",
        "tensor_sha256": tensor_hash, "checked_shots": len(cases), "regular_shots": expected.bit_count(),
        "probe": one_probe,
    })


@pytest.mark.slow
@pytest.mark.parametrize(("reciprocal", "guarded"), [(False, False), (True, False), (True, True)])
def test_padded_phase_software_replay(project_root, monkeypatch, tmp_path, reciprocal, guarded):
    multiply, tensor_hash = _field_product(project_root, monkeypatch, tmp_path)
    cases = _phase_cases(guarded)
    words = [range(i * 12, (i + 1) * 12) for i in range(70)]
    degree = range(840, 846)
    orientations = [i % 2 if reciprocal else 0 for i in range(len(cases))]
    initial = [row[0] + ([bit] if reciprocal else []) for row, bit in zip(cases, orientations, strict=True)]
    live = 847 if reciprocal else 846
    regular = [_regular_chart(row[1]) for row in cases]
    masks = np.random.default_rng(36323).integers(0, 4096, size=(len(cases), 4095))
    results = []
    for seed in (36319, 36329):
        builder = _PhaseBuilder(initial, seed)
        values = builder.data.copy()
        wires = [builder.alloc_bits(12) for _ in range(4095)]
        for register, column in zip(wires, masks.T.tolist(), strict=True):
            for bit, wire in enumerate(register):
                builder.bits[wire] = sum(((word >> bit) & 1) << i for i, word in enumerate(column))
        mask_input = builder.bits.copy()
        degree_padded_residue_scan(builder, None, words[:35], words[35:], wires, degree,
                                   multiply=multiply, orientation=846 if reciprocal else None, guarded=guarded)
        expected = 0
        for i, (_, _, support) in enumerate(cases):
            if guarded and not regular[i]:
                continue
            support = _original_support(support, bool(orientations[i]))
            parity = sum((int(masks[i, position]) & value).bit_count() for position, value in support.items()) % 2
            expected |= parity << i
        assert builder.phase == expected
        assert builder.data[:live] == values and not any(builder.data[live:])
        assert builder.bits == mask_input and builder.controls == [builder.full]
        assert builder.chart_flags == [sum(int(ok) << i for i, ok in enumerate(regular))] * (2 if guarded else 0)
        assert len(builder.data) <= 888
        results.append({"seed": seed, "software_allocated_qubits": len(builder.data),
                        "init_and_calls": builder.charged_ands, "equality_calls": builder.equality_calls})
    write_json(tmp_path / "degree-padding-software.json", {
        "scope": "phase replay with supplied locator, evaluator and degree on regular padded charts",
        "tensor_sha256": tensor_hash, "tested_weights": list(range(36)), "positions": 4095,
        "mask_seed": 36323, "reciprocal_orientation": reciprocal, "guarded": guarded,
        "irregular_weights": [row[0][-1] for row in cases if not _regular_chart(row[1])],
        "observations": results,
    })


@pytest.mark.official
@pytest.mark.slow
@pytest.mark.parametrize(("reciprocal", "guarded"), [(False, False), (True, False), (True, True)])
def test_native_degree_padding_and_phase(project_root, monkeypatch, tmp_path, reciprocal, guarded):
    backend = project_root / "vendor/backend.json"
    if not sys.platform.startswith("linux") or not backend.is_file():
        pytest.skip("pinned native Linux backend required")
    validate_backend(read_json(backend))
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    multiply, tensor_hash = _field_product(project_root, monkeypatch, tmp_path)
    cases = _phase_cases(guarded)

    builder = km.CircuitBuilder()
    loc, omega = [[builder.create_quantum_register(12, f"{name}{i}") for i in range(35)]
                  for name in ("P", "O")]
    deg = builder.create_quantum_register(6, "degree")
    flip = builder.create_quantum_register(1, "orientation") if reciprocal else []
    masks = [builder.create_classical_register(12, f"E{i}") for i in range(4095)]
    degree_padded_residue_scan(builder, km.GF2Field(12), loc, omega, masks, deg, multiply=multiply,
                               orientation=flip[0] if reciprocal else None, guarded=guarded)
    artifact = tmp_path / "padded-scan.kmb"
    builder.finish_circuit().to_file(artifact, format="kmb")
    circuit = km.Circuit.from_file(artifact, format="kmb")
    sim = km.Simulator(batch_size=len(cases), seed=36319, counting_operations=True)
    sim.use_same_registers_as(circuit)
    masks_array = np.random.default_rng(36323).integers(0, 4096, size=(len(cases), 4095))
    orientations = [i % 2 if reciprocal else 0 for i in range(len(cases))]
    initial = [row[0] + ([bit] if reciprocal else []) for row, bit in zip(cases, orientations, strict=True)]
    inputs = np.concatenate((np.asarray(initial), masks_array), axis=1)
    registers = [*loc, *omega, deg, *([flip] if reciprocal else []), *masks]
    for wires, column in zip(registers, inputs.T, strict=True):
        sim.write_across_shots(wires, ((column[None, :] >> np.arange(len(wires))[:, None]) & 1).astype(bool))
    sim.do(circuit)
    for wires, column in zip(registers, inputs.T, strict=True):
        np.testing.assert_array_equal(sim.read_across_shots(wires),
                                      (column[None, :] >> np.arange(len(wires))[:, None]) & 1)
    phase = [sum((value & int(masks_array[i, pos])).bit_count()
                 for pos, value in _original_support(row[2], bool(orientations[i])).items()) % 2
             if not guarded or _regular_chart(row[1]) else 0
             for i, row in enumerate(cases)]
    np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), phase)
    live = {q.id for wires in [*loc, *omega, deg, *([flip] if reciprocal else [])] for q in wires}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not sim.read_across_shots(scratch).any()
    charge = circuit.operation_statistics().num_toffoli_like
    assert sim.operation_statistics().num_toffoli_like == charge * len(cases)
    assert circuit.num_qubits <= 888
    write_json(tmp_path / "degree-padding.json", {
        "scope": "supplied compact locator, evaluator and live degree on regular padded chart",
        "tested_weights": [row[0][-1] for row in cases],
        "backend_sha256": sha256(backend), "tensor_sha256": tensor_hash, "circuit_sha256": sha256(artifact),
        "qubits": circuit.num_qubits, "toffoli_like": charge, "reciprocal_orientation": reciprocal, "guarded": guarded,
    })
