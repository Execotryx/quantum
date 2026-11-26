"""Screen coefficient rounding and a shared reciprocal at the divider checkpoint."""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from invsqrt_checkpoint_joint import CUT, FRACTION, REMAINDER_WIRES, ROOT_WIRES, SCALE_WIRES, WORD_WIRES, decode
from invsqrt_phase_margin import CONTROL, MAX_X, SIMULATOR, verify_rotation_prefix
from qcompile.invsqrt.direct_screen import beta_one_targets, complete_cost, scan_phase
from qcompile.io import read_json, sha256, write_json


COEFFICIENTS = "b030ae5b716ffea3131e4df1db35322aa8e45c13f66d020765d06f93521eac40"
SEED = 61309
TRAIN = 200000
PRECISIONS = (*range(24, 33), FRACTION)
DEGREES = (0, 1, 2, 3)
STAGED_PRECISIONS = ((28, 28), (28, 30), (30, 28), (30, 30), (31, 31))
Integer = NDArray[np.int64]


def evaluate(table: Integer, root: Integer, word: Integer, z: Integer, scale: Integer,
             fraction: int) -> NDArray[np.uint64]:
    intercept, slope, quadratic = table[root - 256].T
    result = intercept + (slope * word + (1 << 18)) // (1 << 19)
    result += (((quadratic * z + 512) // 1024) * z + 512) // 1024
    return result.astype(np.uint64) << (64 - fraction - 10 + scale).astype(np.uint64)


def fit_shared(root: Integer, word: Integer, z: Integer, normal: Integer,
               indices: Integer, degree: int) -> tuple[Integer, list]:
    """Fit numerator coefficients for each root parity over a shared reciprocal."""
    roots = np.arange(256, 512, dtype=np.int64)
    divisors = 4 * (roots // 2) + 2
    table = np.empty((len(roots), 3), dtype=np.float64)
    fits = []
    for parity in (0, 1):
        selected = indices[root[indices] % 2 == parity]
        divisor = divisors[root[selected] - 256]
        design = np.column_stack((np.ones(len(selected)), word[selected] / (1 << 19), (z[selected] / 1024)**2))
        t = (divisor - 768) / 256
        features = np.concatenate([design * t[:, None]**p for p in range(degree + 1)], axis=1)
        y = (1024 / np.sqrt(normal[selected])) * divisor / 512
        fit = np.linalg.lstsq(features, y, rcond=1e-10)[0].reshape(degree + 1, 3)
        d = divisors[parity::2]
        powers = np.column_stack([((d - 768) / 256)**p for p in range(degree + 1)])
        table[parity::2] = (powers @ fit) * (512 / d[:, None])
        fits.append(fit.tolist())
    return np.rint(table * (1 << FRACTION)).astype(np.int64), fits


def run(assembly: Path, simulator: Path, coefficients: Path, output: Path) -> None:
    if (sha256(assembly), sha256(simulator), sha256(coefficients)) != (CONTROL, SIMULATOR, COEFFICIENTS):
        raise ValueError("Wrong pinned assembly, simulator, or coefficient table")
    spec = spec_from_file_location("precision_checkpoint_simulator", simulator)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load the pinned simulator")
    km = module_from_spec(spec)
    spec.loader.exec_module(km)
    ops, register = km.parse_kmx(assembly)
    verify_rotation_prefix(ops, {CUT})
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {"assembly_sha256": CONTROL, "simulator_sha256": SIMULATOR,
        "control_coefficients_sha256": COEFFICIENTS, "driver_sha256": sha256(Path(__file__)),
        "prefix_end": CUT, "legal_inputs": MAX_X, "rounding_precisions": PRECISIONS,
        "shared_numerator_degrees": DEGREES, "seed": SEED, "fit_sample_count": TRAIN,
        "staged_numerator_and_reciprocal_precisions": STAGED_PRECISIONS,
        "reference_for_rotation_projection": {"qubits": 39, "T_like": 1, "fine_rotations": 33,
                                             "retained_cost": 627.2501511112984, "cost_cutoff": 52119.68}})
    sim = km.Sim(39, "zero")
    sim.load_x(register)
    sim.run([op for op in ops if op.line <= CUT])
    states = np.zeros(MAX_X, dtype=np.uint64)
    for wire in set(ROOT_WIRES + SCALE_WIRES + WORD_WIRES):
        states |= km.unpack(sim.Q[wire])[:MAX_X].astype(np.uint64) << np.uint64(wire)
    root = (decode(states, ROOT_WIRES) ^ 1) + 256
    scale = decode(states, SCALE_WIRES)
    word = (decode(states, WORD_WIRES) ^ 1) - 1
    z = decode(states, REMAINDER_WIRES) >> 3
    xs = np.arange(1, MAX_X + 1, dtype=np.int64)
    normal = xs << (2 * scale)
    if np.any((16 * root**2 > normal) | (normal >= 16 * (root + 1)**2)):
        raise ValueError("Root decoding does not match the reference")
    target, tolerance = beta_one_targets(xs)

    def targets(chunk: Integer):
        return target[chunk - 1], tolerance[chunk - 1]

    rounded = []
    shared = []
    staged = []

    def check_phase(phase: NDArray[np.uint64], name: str) -> dict:
        result = scan_phase(lambda chunk: phase[chunk - 1], MAX_X, targets)
        margin = result["minimum_margin_phase64"]
        if margin > 0:
            charge = complete_cost(39, (0, 1, 33), margin)["score"] / 39
            result["rotation_and_T_projection"] = charge
            result["available_arithmetic_projection"] = 52119.68 / 39 - 627.2501511112984 - charge
        print(name, result["failed_inputs"], result["worst_tolerance_fraction"], flush=True)
        return result

    def check(table: Integer, fraction: int, name: str) -> dict:
        candidate = output / f"{name}.json"
        write_json(candidate, table.tolist())
        result = check_phase(evaluate(table, root, word, z, scale, fraction), name)
        return {"coefficients_sha256": sha256(candidate), "fraction_bits": fraction,
                "coefficient_widths": [max(abs(int(v)) for v in col).bit_length() for col in table.T], **result}

    base = np.asarray(read_json(coefficients), dtype=np.int64)
    for fraction in PRECISIONS:
        shift = FRACTION - fraction
        table = (base + ((1 << shift) // 2)) >> shift
        rounded.append(check(table, fraction, f"round-{fraction}"))
    indices = np.sort(np.random.default_rng(SEED).choice(MAX_X, TRAIN, replace=False))
    for degree in DEGREES:
        table, fit = fit_shared(root, word, z, normal, indices, degree)
        result = check(table, FRACTION, f"shared-{degree}")
        shared.append({"numerator_degree": degree, "normalized_numerator_fits_by_parity": fit, **result})
    # The degree-zero fit uses one reciprocal per adjacent even/odd root
    # pair. Round the numerator and reciprocal independently before their
    # product, so the test includes rounding at the actual stage boundaries.
    constants = np.asarray(shared[0]["normalized_numerator_fits_by_parity"], dtype=np.float64)[:, 0]
    d = 4 * np.arange(128, 256, dtype=np.int64) + 2
    for numerator_bits, reciprocal_bits in STAGED_PRECISIONS:
        numerators = np.rint(constants * (1 << numerator_bits)).astype(np.int64)
        reciprocals = ((512 << reciprocal_bits) + d // 2) // d
        intercept, slope, quadratic = numerators[root & 1].T
        h = intercept + (slope * word + (1 << 18)) // (1 << 19)
        h += (((quadratic * z + 512) // 1024) * z + 512) // 1024
        delta = h - (1 << numerator_bits)
        # Distribute the known unity: only the much smaller correction
        # word reaches the multiplier, and the unity term is an addition.
        g = reciprocals[(root - 256) >> 1]
        result = ((g << numerator_bits) + g * delta + (1 << (reciprocal_bits - 1))) >> reciprocal_bits
        phase = result.astype(np.uint64) << (64 - numerator_bits - 10 + scale).astype(np.uint64)
        name = f"staged-{numerator_bits}-{reciprocal_bits}"
        path = output / f"{name}.json"
        write_json(path, {"numerator_coefficients_by_parity": numerators.tolist(), "reciprocal_rows": reciprocals.tolist()})
        staged.append({"numerator_bits": numerator_bits, "reciprocal_bits": reciprocal_bits,
                       "coefficient_sha256": sha256(path), "delta_range": [int(delta.min()), int(delta.max())],
                       **check_phase(phase, name)})
    write_json(output / "screen.json", {"registration_sha256": sha256(registration),
        "rounded": rounded, "shared_reciprocal": shared, "staged_reciprocal": staged,
        "scope": "numerical phase only; coefficient production and reversible arithmetic unpriced"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "simulator", "coefficients", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
