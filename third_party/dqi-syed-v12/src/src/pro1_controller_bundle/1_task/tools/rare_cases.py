"""Deterministic, algebraically certified DQI stress cases from the attached graph.

Copyright 2026 Syed Asad Ali.
SPDX-License-Identifier: Apache-2.0

No circuit is loaded here. Field tables and all cases are derived from formulas.
The field and confluent-node conventions follow the supplied Apache-2.0 decoder
kit. New implementation copyright is stated above.

This is a targeted finite test corpus, not a proof of full decoder exactness.
In particular, early retained-node poles do not replace tests of late PCC
reconstruction or the separate final-pole reconstruction approximation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import cached_property
import random
from typing import Any


@dataclass
class Case:
    label: str
    positions: list[int]
    values: list[int]
    certificate: dict[str, Any] = field(default_factory=dict)
    mask_mode: str = "random"
    mask_values: list[int] | None = None

    def validate(self) -> None:
        if not (len(self.positions) == len(self.values) <= 35):
            raise ValueError("A case must have matching lists and weight at most 35")
        if len(set(self.positions)) != len(self.positions):
            raise ValueError("Error positions must be distinct")
        if any(not 0 <= p < 4095 for p in self.positions):
            raise ValueError("Error positions are outside the benchmark range")
        if any(not 1 <= v < 4096 for v in self.values):
            raise ValueError("Error values must be nonzero GF(2^12) elements")
        if self.mask_mode not in ("random", "zero", "all", "one_hot", "recorded"):
            raise ValueError("Unknown structured mask mode")
        if self.mask_mode == "recorded":
            if self.mask_values is None or len(self.mask_values) != 4095:
                raise ValueError("Recorded masks must contain all 4095 field values")
            if any(not 0 <= value < 4096 for value in self.mask_values):
                raise ValueError("Recorded masks are outside GF(2^12)")
        elif self.mask_values is not None:
            raise ValueError("Explicit masks require recorded mask mode")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        result = asdict(self)
        if self.mask_values is None:
            del result['mask_values']
        return result


class GF12:
    """Polynomial-basis GF(2^12), modulus x^12+x^6+x^4+x+1.

    The quadratic extension uses y^2+y+2048 = 0. All tables are generated.
    """

    degree = 12
    size = 1 << degree
    mask = size - 1
    modulus = (1 << 12) | (1 << 6) | (1 << 4) | (1 << 1) | 1
    extension_constant = 1 << 11

    def __init__(self) -> None:
        self.exp: list[int] = []
        self.log = [-1] * self.size
        x = 1
        for i in range(self.mask):
            if self.log[x] >= 0:
                raise AssertionError("The chosen polynomial basis is not primitive")
            self.exp.append(x)
            self.log[x] = i
            x <<= 1
            if x & self.size:
                x ^= self.modulus
        if x != 1:
            raise AssertionError("Incorrect multiplicative group order")
        self.exp *= 2
        if self.trace(self.extension_constant) != 1:
            raise AssertionError("The quadratic extension must be irreducible")

    def mul(self, a: int, b: int) -> int:
        return self.exp[self.log[a] + self.log[b]] if a and b else 0

    def inv(self, a: int) -> int:
        return self.exp[self.mask - self.log[a]] if a else 0

    def square(self, a: int) -> int:
        return self.mul(a, a)

    def trace(self, a: int) -> int:
        out = 0
        for _ in range(self.degree):
            out ^= a
            a = self.square(a)
        if out not in (0, 1):
            raise AssertionError("Invalid field trace")
        return out

    def emul(self, x: int, y: int) -> int:
        a, b = x & self.mask, x >> self.degree
        c, d = y & self.mask, y >> self.degree
        bd = self.mul(b, d)
        return (self.mul(a, c) ^ self.mul(self.extension_constant, bd)) | (
            (self.mul(a, d) ^ self.mul(b, c) ^ bd) << self.degree
        )

    def einv(self, x: int) -> int:
        a, b = x & self.mask, x >> self.degree
        norm = self.square(a) ^ self.mul(a, b) ^ self.mul(
            self.extension_constant, self.square(b)
        )
        ni = self.inv(norm)
        return self.mul(a ^ b, ni) | (self.mul(b, ni) << self.degree)

    def escale(self, x: int, c: int) -> int:
        return self.mul(x & self.mask, c) | (
            self.mul(x >> self.degree, c) << self.degree
        )

    def eval(self, polynomial: list[int], x: int) -> int:
        out = 0
        for coefficient in reversed(polynomial):
            out = self.emul(out, x) ^ coefficient
        return out

    @staticmethod
    def trim(p: list[int]) -> list[int]:
        while len(p) > 1 and p[-1] == 0:
            p.pop()
        return p or [0]

    def add(self, a: list[int], b: list[int]) -> list[int]:
        out = [0] * max(len(a), len(b))
        for i, value in enumerate(a):
            out[i] ^= value
        for i, value in enumerate(b):
            out[i] ^= value
        return self.trim(out)

    def scale(self, p: list[int], c: int) -> list[int]:
        return self.trim([self.mul(v, c) for v in p])

    def multiply(self, a: list[int], b: list[int]) -> list[int]:
        out = [0] * (len(a) + len(b) - 1)
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                out[i + j] ^= self.mul(x, y)
        return self.trim(out)

    def divide(self, a: list[int], b: list[int]) -> tuple[list[int], list[int]]:
        a, b = self.trim(list(a)), self.trim(list(b))
        if b == [0]:
            raise ZeroDivisionError("Polynomial division by zero")
        q = [0] * max(1, len(a) - len(b) + 1)
        inverse_lead = self.inv(b[-1])
        while a != [0] and len(a) >= len(b):
            shift = len(a) - len(b)
            value = self.mul(a[-1], inverse_lead)
            q[shift] = value
            for j, coefficient in enumerate(b):
                a[shift + j] ^= self.mul(value, coefficient)
            self.trim(a)
        return self.trim(q), a

    @cached_property
    def kappas(self) -> list[int]:
        return [self.square(2 * g) ^ (2 * g) ^ self.extension_constant for g in range(17)]

    @cached_property
    def quadratic_roots(self) -> dict[int, int]:
        out: dict[int, int] = {}
        for z in range(self.size):
            out.setdefault(self.square(z) ^ z, z)
        return out


def rational_pair(f: GF12, roots: list[int], residues: list[int]) -> tuple[list[int], list[int]]:
    denominator = [1]
    for root in roots:
        denominator = f.multiply(denominator, [root, 1])
    numerator = [0]
    for root, residue in zip(roots, residues):
        quotient, remainder = f.divide(denominator, [root, 1])
        if remainder != [0]:
            raise AssertionError("Root denominator division was not exact")
        numerator = f.add(numerator, f.scale(quotient, residue))
    return numerator, denominator


def prefix_heads(
    f: GF12, numerator: list[int], denominator: list[int], count: int
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Exact rational recurrence, stopping instead of silently crossing a pole."""
    heads = []
    for h in range(count):
        c = 2 * (h // 2)
        gamma = c | f.size
        divisor = f.eval(denominator, gamma)
        if divisor == 0:
            raise ValueError(f"Rational chart has a pole before head {h}")
        value = f.emul(f.eval(numerator, gamma), f.einv(divisor))
        b = value >> f.degree
        a = (value & f.mask) ^ f.mul(c, b)
        heads.append((a, b))
        combined = f.add(numerator, f.multiply(denominator, [a, b]))
        quotient, remainder = f.divide(combined, [f.kappas[h // 2], 1, 1])
        if remainder != [0]:
            raise AssertionError("Confluent interpolation did not divide exactly")
        numerator, denominator = denominator, quotient
    return heads, numerator, denominator


def solve_affine(
    f: GF12, coefficients: list[list[int]], rhs: list[int], rng: random.Random
) -> tuple[list[int], int]:
    """Deterministic pivot order; random free coordinates use a fixed corpus seed."""
    n = len(coefficients[0])
    rows = [list(row) + [value] for row, value in zip(coefficients, rhs)]
    pivots = []
    for column in range(n):
        pivot = next((r for r in range(len(pivots), len(rows)) if rows[r][column]), None)
        if pivot is None:
            continue
        r = len(pivots)
        rows[r], rows[pivot] = rows[pivot], rows[r]
        inverse = f.inv(rows[r][column])
        rows[r] = [f.mul(v, inverse) for v in rows[r]]
        for j in range(len(rows)):
            if j != r and rows[j][column]:
                factor = rows[j][column]
                rows[j] = [x ^ f.mul(factor, y) for x, y in zip(rows[j], rows[r])]
        pivots.append(column)
    if any(not any(row[:n]) and row[-1] for row in rows):
        raise ValueError("Inconsistent event constraints")
    free = [column for column in range(n) if column not in pivots]
    solution = [0] * n
    for column in free:
        solution[column] = rng.randrange(1, f.size)
    for r, pivot in enumerate(pivots):
        value = rows[r][-1]
        for column in free:
            value ^= f.mul(rows[r][column], solution[column])
        solution[pivot] = value
    if any(
        value != _dot(f, row, solution)
        for row, value in zip(coefficients, rhs)
    ):
        raise AssertionError("Event system failed its exact residual check")
    return solution, len(pivots)


def _dot(f: GF12, row: list[int], values: list[int]) -> int:
    out = 0
    for a, b in zip(row, values):
        out ^= f.mul(a, b)
    return out


def initial_jets(f: GF12, roots: list[int], residues: list[int]) -> list[tuple[int, int]]:
    jets = []
    for g in range(17):
        gamma = (2 * g) | f.size
        u = v = 0
        for root, weight in zip(roots, residues):
            inverse = f.einv(root ^ gamma)
            u ^= f.escale(inverse, weight)
            v ^= f.escale(f.emul(inverse, inverse), weight)
        jets.append((u, v))
    return jets


def extraction_events(
    f: GF12, roots: list[int], residues: list[int], *, jet_groups: int = 3
) -> dict[str, Any]:
    """Classify the field recurrence with actual pole flags (before drops).

    This is an input-class certificate, not a simulation of measurement phases
    or an assertion that the approximate H3N graph follows the ideal chart.
    The default is H3N's HS=3 split; HS=4 recovers the historical audit model.
    """
    if jet_groups not in (3, 4):
        raise ValueError('Only the selected and historical audit splits are supported')
    heads: list[tuple[int, int]] = []
    events: list[dict[str, Any]] = []
    poles: list[bool] = []
    first_values: list[int] = []
    for g, (u, v) in enumerate(initial_jets(f, roots, residues)):
        c = 2 * g
        if g < jet_groups:
            for h, (a, b) in enumerate(heads):
                q = f.kappas[h // 2] ^ f.kappas[g]
                translated = (a ^ f.mul(c, b)) | (b << f.degree)
                u ^= translated
                v ^= b
                if not u:
                    events.append({"kind": "jet_zero", "group": g, "head": h, "derivative_nonzero": bool(v)})
                inverse = f.einv(u)
                safe_inverse = inverse ^ int(u == 0)
                v = f.emul(v, f.emul(safe_inverse, safe_inverse))
                v = inverse ^ f.escale(v, q)
                u = f.escale(inverse, q)
            pole = False
        else:
            n, d, ell, correction = u, 1, v, 0
            for h, (a, b) in enumerate(heads):
                q = f.kappas[h // 2] ^ f.kappas[g]
                value = (a ^ f.mul(c, b)) | (b << f.degree)
                corrected = b ^ f.escale(value, correction)
                ell = f.escale(ell ^ f.emul(corrected, f.emul(d, d)), q)
                n, d = f.escale(d, q), n ^ f.emul(value, d)
                correction ^= f.inv(q)
                if not n:
                    events.append({"kind": "mid_chain_zero", "group": g, "after_heads": h + 1})
            if correction:
                raise AssertionError("Paired node correction must close")
            pole = d == 0
            if pole:
                events.append({"kind": "chain_pole", "group": g, "chance": len(roots) > 2 * g - 1})
                n, d = d, n
            if not d:
                raise AssertionError("A projective pair cannot vanish together")
            inverse = f.einv(d)
            u = f.emul(n, inverse)
            v = f.emul(ell, f.emul(inverse, inverse))
        poles.append(pole)
        first_values.append(u)
        a, b = (u & f.mask) ^ f.mul(c, u >> f.degree), u >> f.degree
        local = v ^ b
        if local == 0:
            events.append({"kind": "local_inverse_zero", "group": g, "chance": len(roots) > 2 * g})
        inverse = f.einv(local)
        heads.extend([(a, b), ((inverse & f.mask) ^ f.mul(c, inverse >> f.degree), inverse >> f.degree)])
    n = ell = 0
    for root, weight in zip(roots, residues):
        inverse = f.inv(root)
        n ^= f.mul(weight, inverse)
        ell ^= f.mul(weight, f.square(inverse))
    d, correction = 1, 0
    for h, (a, b) in enumerate(heads):
        q = f.kappas[h // 2]
        ell = f.mul(q, ell ^ f.mul(b ^ f.mul(a, correction), f.square(d)))
        n, d = f.mul(q, d), n ^ f.mul(a, d)
        correction ^= f.inv(q)
    main_pole = d == 0
    if main_pole:
        events.append({"kind": "trailing_pole"})
    relations = [
        {"predecessor": g, "actual": poles[g], "reconstructed": first_values[g] == 0 and poles[g + 1]}
        for g in range(jet_groups, 16)
        if poles[g] != (first_values[g] == 0 and poles[g + 1])
    ]
    p16_bad = poles[16] != (first_values[16] == 0 and main_pole)
    return {"events": events, "pcc_relation_violations": relations, "p16_relation_violation": p16_bad}


def residue_case(
    f: GF12, label: str, roots: list[int], residues: list[int], certificate: dict[str, Any]
) -> Case:
    values = []
    for root, weight in zip(roots, residues):
        # P(x)=x^2 product_g (x^2+x+kappa_g)^2, and residue=e*x*P(x).
        polynomial_value = f.square(root)
        for kappa in f.kappas:
            polynomial_value = f.mul(polynomial_value, f.square(f.square(root) ^ root ^ kappa))
        denominator = f.mul(root, polynomial_value)
        if not denominator:
            raise AssertionError("Benchmark roots do not meet the node polynomial")
        values.append(f.mul(weight, f.inv(denominator)))
    case = Case(label, [f.log[root] for root in roots], values, certificate)
    case.validate()
    return case


def constrained_case(
    f: GF12, rng: random.Random, kind: str, group: int, serial: int
) -> Case:
    """Force a rational denominator zero by a small exact affine field solve."""
    count = {"jet_zero": 1, "local_inverse_zero": 2 * group + 1,
             "chain_pole": 2 * group, "mid_chain_zero": 1}[kind]
    for attempt in range(100):
        roots = rng.sample(range(1, f.size), 35)
        anchor = [rng.randrange(1, f.size) for _ in roots]
        numerator, denominator = rational_pair(f, roots, anchor)
        try:
            heads, _, _ = prefix_heads(f, numerator, denominator, count)
        except ValueError:
            continue
        n_basis = [[0]] + [f.divide(denominator, [root, 1])[0] for root in roots]
        d_basis = [denominator] + [[0] for _ in roots]
        rows: list[list[int]] = []
        rhs: list[int] = []
        for h, (a, b) in enumerate(heads):
            quotients, remainders = [], []
            for n, d in zip(n_basis, d_basis):
                quotient, remainder = f.divide(f.add(n, f.multiply(d, [a, b])), [f.kappas[h // 2], 1, 1])
                quotients.append(quotient)
                remainders.append(remainder + [0] * (2 - len(remainder)))
            for coordinate in range(2):
                rows.append([r[coordinate] for r in remainders[1:]])
                rhs.append(remainders[0][coordinate])
            n_basis, d_basis = d_basis, quotients
        gamma = (2 * group) | f.size
        evaluations = [f.eval(p, gamma) for p in d_basis]
        for shift in (0, f.degree):
            rows.append([(value >> shift) & f.mask for value in evaluations[1:]])
            rhs.append((evaluations[0] >> shift) & f.mask)
        try:
            residues, rank = solve_affine(f, rows, rhs, rng)
            if not all(residues):
                continue
            final_n, final_d = rational_pair(f, roots, residues)
            actual_heads, _, reduced_d = prefix_heads(f, final_n, final_d, count)
            if actual_heads != heads or f.eval(reduced_d, gamma) != 0:
                raise AssertionError("The forced pole lacks an exact rational certificate")
            classified = extraction_events(f, roots, residues)
        except ValueError:
            continue
        matching = [e for e in classified["events"] if e["kind"] == kind and e.get("group") == group]
        if kind == "mid_chain_zero":
            matching = [e for e in matching if e["after_heads"] == 2]
            if any(e["kind"] == "chain_pole" and e.get("group") == group for e in classified["events"]):
                continue
        if not matching:
            continue
        certificate = {"construction": "exact affine GF(2^12) constraints", "rank": rank,
                       "free_variables": len(roots) - rank, "prefix_heads": count,
                       "target_group": group, "target_denominator_value": 0,
                       "attempt": attempt, **classified}
        return residue_case(f, f"{kind}_g{group}_{serial}", roots, residues, certificate)
    raise RuntimeError(f"Could not construct certified {kind} group {group}")


def root_gap(f: GF12, roots: list[int]) -> tuple[int, list[int]]:
    _, polynomial = rational_pair(f, roots, [1] * len(roots))
    if len(polynomial) != 36 or polynomial[-1] != 1:
        raise ValueError("Root converter gap construction uses weight 35")
    # Frobenius maps preserve zero: test pre-square-root coefficients exactly.
    even, odd = polynomial[:-1:2], polynomial[1:-1:2]
    residual = [even[i] ^ f.mul(even[-1], odd[i]) for i in range(len(odd))]
    leading_zeros = 0
    for value in reversed(residual):
        if value:
            break
        leading_zeros += 1
    return 1 + leading_zeros, residual


def gap_case(f: GF12, rng: random.Random, gap: int, serial: int) -> Case:
    for attempt in range(100):
        if gap == 2:
            base = rng.sample(range(1, f.size), 33)
            _, polynomial = rational_pair(f, base, [1] * len(base))
            a, b, c = polynomial[-2:-5:-1]
            roots = None
            for pair_sum in range(1, f.size):
                pair_product = f.mul(c ^ f.mul(a, b), f.inv(pair_sum)) ^ f.mul(a, pair_sum ^ a)
                normalized = f.mul(pair_product, f.inv(f.square(pair_sum)))
                z = f.quadratic_roots.get(normalized)
                if z is None:
                    continue
                x = f.mul(pair_sum, z)
                y = x ^ pair_sum
                if x == 0 or y == 0 or x in base or y in base:
                    continue
                candidate = base + [x, y]
                if root_gap(f, candidate)[0] == 2:
                    roots = candidate
                    break
            if roots is None:
                continue
        else:
            # Seventeen pairs {r,r+1}. Their quadratic constants sum to zero
            # when the xor of the seventeen representatives is zero.
            representatives = rng.sample(range(2, f.size, 2), 16)
            last = 0
            for value in representatives:
                last ^= value
            if last == 0 or last in representatives:
                continue
            representatives.append(last)
            roots = [value for representative in representatives for value in (representative, representative ^ 1)]
            extra = next(value for value in range(1, f.size) if value not in roots)
            roots.append(extra)
        actual_gap, residual = root_gap(f, roots)
        if actual_gap < gap:
            raise AssertionError("Algebraic root-gap construction failed")
        residues = [rng.randrange(1, f.size) for _ in roots]
        numerator, denominator = rational_pair(f, roots, residues)
        try:
            prefix_heads(f, numerator, denominator, 34)
        except ValueError:
            continue
        certificate = {"construction": "distinct error roots with exact locator coefficient constraints",
                       "root_gap": actual_gap, "root_residual_leading_coefficients": residual[-3:],
                       "root_zero_after_single_pivot": actual_gap >= 3,
                       "distinct_nonzero_roots": True, "regular_first_34_rational_heads": True,
                       "attempt": attempt, **extraction_events(f, roots, residues)}
        return residue_case(f, f"converter_gap_{'2' if gap == 2 else 'ge3'}_{serial}", roots, residues, certificate)
    raise RuntimeError("Could not construct converter gap case")


def generate_rare_cases(seed: int, per_class: int = 8) -> tuple[list[Case], dict[str, Any]]:
    if per_class < 1:
        raise ValueError("per_class must be positive")
    f, rng, cases = GF12(), random.Random(seed), []
    for i in range(per_class):
        cases.append(constrained_case(f, rng, "jet_zero", 1 + i % 2, i))
        cases.append(constrained_case(f, rng, "local_inverse_zero", i % 3, i))
        cases.append(constrained_case(f, rng, "chain_pole", 3 + i % 6, i))
        cases.append(constrained_case(f, rng, "mid_chain_zero", 9 + i % 8, i))
        cases.append(gap_case(f, rng, 2, i))
        cases.append(gap_case(f, rng, 3, i))
        roots = rng.sample(range(1, f.size), 33)
        residues = [rng.randrange(1, f.size) for _ in roots]
        classified = extraction_events(f, roots, residues)
        if not any(e["kind"] == "trailing_pole" for e in classified["events"]):
            raise AssertionError("The k=33 trailing-pole control was not classified")
        cases.append(residue_case(f, f"trailing_pole_k33_{i}", roots, residues,
                                 {"construction": "fixed odd weight 33", **classified}))
    coverage = {
        "generated_cases": len(cases),
        "constructed_classes": ["jet_zero", "local_inverse_zero", "chance_chain_pole_groups_3_to_8",
                                "converter_gap_2", "converter_gap_ge3_at_root_including_root_zero",
                                "trailing_pole", "mid_chain_zero"],
        "limitations": [
            "The historical mc_hs3/mc_hs4 .ev corpus is absent from the attachment; this is a fresh corpus.",
            "No claim of complete late-node chance-pole/PCC relation or final-pole reconstruction exception coverage.",
            "Root converter gap tests do not cover every internal converter gap site or every gap length.",
            "Field recurrence certificates identify input events; they do not certify quantum phase correctness.",
            "Passing a finite corpus does not prove zero errors for every input or every salt.",
        ],
    }
    return cases, coverage


def generate_structured_cases() -> list[Case]:
    cases = []
    for weight in range(36):
        patterns = (
            ("low_contiguous_ones", list(range(weight)), [1] * weight, "random"),
            ("high_contiguous_full", list(range(4095 - weight, 4095)), [4095] * weight, "all"),
            ("spread_basis", [(137 * j + 71) % 4095 for j in range(weight)],
             [1 << (j % 12) for j in range(weight)], "one_hot"),
            ("zero_masks", [(173 * j + 109) % 4095 for j in range(weight)],
             [1 + (31 * j) % 4095 for j in range(weight)], "zero"),
        )
        for name, positions, values, mask_mode in patterns:
            case = Case(f"structured_k{weight}_{name}", positions, values,
                        {"weight": weight, "pattern": name}, mask_mode)
            case.validate()
            cases.append(case)
    return cases
