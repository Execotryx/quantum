"""Compare D4's ordinary extraction words with independent rational arithmetic."""

import argparse
from pathlib import Path

from qcompile.dqi.decoder import _add, _divide, _multiply, decode, syndrome
from qcompile.dqi.double_node_pole import join_local_pole, split_local_pole
from qcompile.dqi.field import GF4096
from qcompile.io import read_json, sha256, write_json


class ExternalField:
    """The pinned quadratic extension with y² + y = 2048."""

    def __init__(self, base: GF4096):
        self.base = base

    def mul(self, a: int, b: int) -> int:
        mul = self.base.mul
        lo, hi, other_lo, other_hi = a & 4095, a >> 12, b & 4095, b >> 12
        product = mul(hi, other_hi)
        return (mul(lo, other_lo) ^ mul(2048, product)) | (
            (mul(lo, other_hi) ^ mul(hi, other_lo) ^ product) << 12
        )

    def inv(self, a: int) -> int:
        if not a:
            return 0
        lo, hi = a & 4095, a >> 12
        conjugate = (lo ^ hi) | (hi << 12)
        norm = self.mul(a, conjugate)
        return self.mul(conjugate, self.base.inv(norm))

    def evaluate(self, poly: list[int], a: int) -> int:
        value = 0
        for coefficient in reversed(poly):
            value = self.mul(value, a) ^ coefficient
        return value


def original_pair(errors: dict[int, int], kappas: list[int], field: GF4096):
    geometry = node_polynomial(kappas, field)
    denominator = [1]
    for position in errors:
        denominator = _multiply(denominator, [field.exp[position], 1], field)
    numerator = [0]
    for position, value in errors.items():
        root = field.exp[position]
        quotient, remainder = _divide(denominator, [root, 1], field)
        if remainder != [0]:
            raise ValueError("Recovered support does not divide the reference denominator")
        residue = field.mul(field.mul(value, root), field.evaluate(geometry, root))
        numerator = _add(numerator, [field.mul(residue, coefficient) for coefficient in quotient])
    return numerator, denominator


def node_polynomial(kappas: list[int], field: GF4096) -> list[int]:
    polynomial = [0, 0, 1]
    for kappa in kappas:
        polynomial = _multiply(polynomial, [kappa, 1, 1], field)
    return polynomial


def doubled_node_fixtures() -> list[dict]:
    """Construct valid supports with early poles by solving two linear constraints."""
    field = GF4096()
    ext = ExternalField(field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    geometry = node_polynomial(kappas, field)
    positions = (1, 2, 3)
    first_node = 4096
    rows = []
    for group in range(8):
        matrix = []
        for position in positions:
            root = field.exp[position]
            residue = field.mul(root, field.evaluate(geometry, root))
            first_inverse = ext.inv(first_node ^ root)
            first = ext.mul(residue, first_inverse)
            if group:
                node = (2 * group) | 4096
                forced_zero = ext.mul(residue, ext.inv(node ^ root)) ^ (first & 4095) ^ ext.mul(first >> 12, node)
            else:
                forced_zero = ext.mul(residue, ext.mul(first_inverse, first_inverse)) ^ (first >> 12)
            matrix.append((forced_zero & 4095, forced_zero >> 12))
        weights = [
            field.mul(matrix[(i + 1) % 3][0], matrix[(i + 2) % 3][1])
            ^ field.mul(matrix[(i + 2) % 3][0], matrix[(i + 1) % 3][1])
            for i in range(3)
        ]
        if not all(weights):
            raise ValueError("Degenerate exact-pole fixture")
        errors: dict[int, int] = dict(zip(positions, weights, strict=True))
        rows.append({
            "group": group, "kind": "local" if group == 0 else "intermediate",
            "error_positions": positions, "error_values": weights, "syndrome": syndrome(errors, field),
        })
    return rows


def derivative(poly: list[int]) -> list[int]:
    return [coefficient if power % 2 else 0 for power, coefficient in enumerate(poly[1:], 1)]


def paired_reference(syndrome_words: list[int], field: GF4096) -> dict:
    """Follow finite and second-head pole charts until termination or a first-head pole."""
    ext = ExternalField(field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    n, d = original_pair(decode(syndrome_words, field), kappas, field)
    words, pole_groups = [], []
    pair_input = n, d
    for head, kappa in enumerate(kappas):
        c = head // 2 * 2
        node = c | 4096
        if head % 2 == 0:
            pair_input = n, d
        divisor = ext.evaluate(d, node)
        if not divisor:
            if head % 2 == 0:
                return {"words": words, "pole_groups": pole_groups, "first_head_pole": head}
            n, d = split_local_pole(pair_input[0], pair_input[1], words[-2:], kappa, field)
            words.extend([0, 0])
            pole_groups.append(head // 2)
            continue
        value = ext.mul(ext.evaluate(n, node), ext.inv(divisor))
        head_words = [(value & 4095) ^ field.mul(value >> 12, c), value >> 12]
        words.extend(head_words)
        residual = _add(n, _multiply(head_words, d, field))
        if residual == [0]:
            return {"words": words, "pole_groups": pole_groups, "termination": head}
        q, remainder = _divide(residual, [kappa, 1, 1], field)
        if remainder != [0]:
            raise ValueError("Paired reference left a remainder at its node")
        n, d = d, q
    return {"words": words, "pole_groups": pole_groups, "tail": [n, d]}


def audit_case(case: dict, native: dict, field: GF4096) -> dict:
    ext = ExternalField(field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    errors = decode(case["syndrome"], field)
    parity = sum((case["mask"][j] & value).bit_count() for j, value in errors.items()) % 2
    if bool(parity) != case["expected_phase"]:
        raise ValueError("Recovered error mask parity disagrees with the official verifier")
    numerator, denominator = original_pair(errors, kappas, field)
    reference, poles, trace = [], [], []
    paired_pole = None
    n, d = numerator, denominator
    pair_input = n, d
    termination = None
    for head, kappa in enumerate(kappas):
        if head % 2 == 0:
            pair_input = n, d
        c = head // 2 * 2
        node = c | 4096
        divisor = ext.evaluate(d, node)
        if not divisor:
            poles.append({"head": head, "degree": len(d) - 1})
            if head % 2:
                first_head = reference[-2:]
                next_n, next_d = split_local_pole(pair_input[0], pair_input[1], first_head, kappa, field)
                if join_local_pole(next_n, next_d, first_head, kappa, field) != pair_input:
                    raise ValueError("Doubled-node pole transfer did not round trip")
                paired_pole = {"head": head, "continuation_degrees": [len(next_n) - 1, len(next_d) - 1]}
            break
        value = ext.mul(ext.evaluate(n, node), ext.inv(divisor))
        head_words = [(value & 4095) ^ field.mul(value >> 12, c), value >> 12]
        reference.extend(head_words)
        residual = _add(n, _multiply(head_words, d, field))
        if residual == [0]:
            termination = head
            reference.extend([0] * (68 - len(reference)))
            break
        quotient, remainder = _divide(residual, [kappa, 1, 1], field)
        if remainder != [0]:
            raise ValueError("Rational head did not cancel at its node")
        future_poles = [
            i for i in range(head + 1, len(kappas)) if not ext.evaluate(quotient, (i // 2 * 2) | 4096)
        ]
        if future_poles:
            trace.append({"after_head": head, "degree": len(quotient) - 1, "future_poles": future_poles})
        n, d = d, quotient

    ordinary_words, ordinary_zeros = [], []
    d_numerator, d_denominator = derivative(numerator), derivative(denominator)
    for c in range(0, 16, 2):
        node = c | 4096
        inv = ext.inv(ext.evaluate(denominator, node))
        u = ext.mul(ext.evaluate(numerator, node), inv)
        v = ext.mul(ext.evaluate(d_numerator, node) ^ ext.mul(u, ext.evaluate(d_denominator, node)), inv)
        for head in range(c):
            lo, hi = ordinary_words[2 * head:2 * head + 2]
            u ^= (lo ^ field.mul(c, hi)) | (hi << 12)
            v ^= hi
            if not u and v:
                ordinary_zeros.append({"group": c // 2, "source_head": head, "derivative": v})
            u_inverse = ext.inv(u)
            scaled = ext.mul(v, ext.mul(u_inverse, u_inverse)) if u else v
            factor = kappas[head] ^ kappas[c]
            u, v = ext.mul(factor, u_inverse), ext.mul(factor, scaled) ^ u_inverse
        ordinary_words.extend([(u & 4095) ^ field.mul(c, u >> 12), u >> 12])
        local = v ^ (u >> 12)
        if not local:
            ordinary_zeros.append({"group": c // 2, "local_head": c + 1})
        local_inv = ext.inv(local)
        ordinary_words.extend([(local_inv & 4095) ^ field.mul(c, local_inv >> 12), local_inv >> 12])

    observed = native["extraction_words"]
    mismatches = [
        {
            "head": head, "native": observed[2 * head:2 * head + 2],
            "rational": reference[2 * head:2 * head + 2],
        }
        for head in range(len(reference) // 2)
        if observed[2 * head:2 * head + 2] != reference[2 * head:2 * head + 2]
    ]
    return {
        "index": case["index"], "phase_error": case["phase_error"], "error_weight": len(errors),
        "termination_head": termination, "rational_poles": poles, "residuals_with_future_poles": trace,
        "local_pole_transfer": paired_pole,
        "ordinary_zero_events": ordinary_zeros, "native_matches_ordinary_words": observed[:32] == ordinary_words,
        "ordinary_words": ordinary_words, "first_native_rational_mismatch": mismatches[0] if mismatches else None,
    }


def audit(profile: Path, replay: Path, output: Path) -> None:
    native = read_json(profile)
    if native["homogeneous_ablation"]:
        raise ValueError("The ordinary oracle comparison needs the banked control")
    field = GF4096()
    rows = []
    for draw, receipt in native["batch_receipts"].items():
        for name, digest in receipt["batches"].items():
            path = replay / draw / name
            if sha256(path) != digest:
                raise ValueError("Captured batch differs from the native profile")
            batch = read_json(path)
            for case in batch["shots"] + batch["controls"]:
                observed, = (
                    row for row in native["profiles"] if row["draw"] == draw and row["index"] == case["index"]
                )
                rows.append({"draw": draw, **audit_case(case, observed, field)})
    write_json(output, {"native_profile_sha256": sha256(profile), "cases": rows})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit(args.profile, args.replay, args.output)


if __name__ == "__main__":
    main()
