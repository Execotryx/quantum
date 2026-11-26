"""Fit fixed-point joint root/remainder phase models on the pinned divider cut."""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from invsqrt_checkpoint_phase import CUT
from invsqrt_phase_margin import CONTROL, MAX_X, SIMULATOR, verify_rotation_prefix
from qcompile.invsqrt.direct_screen import beta_one_targets, scan_phase
from qcompile.io import sha256, write_json


LINEAR_WIRES = tuple(range(15)) + (25, 26, 27, 28)
ROOT_WIRES = (22, *range(15, 22))
SCALE_WIRES = (23, 24, 34, 35)
REMAINDER_WIRES = tuple(range(2, 15))
FRACTION = 40
FORMATS = (("bits", 2, 8), ("bits", 2, 9), ("bits", 2, 11), ("bits", 3, 13),
           *(("word", 2, width) for width in range(9, 14)), ("word", 3, 13),
           ("word-and-low", 2, 9), ("word-and-low", 2, 13))
WORD_WIRES = (28, 27, 26, 25, *range(15))
LOW_WIRES = (*range(6), 25, 26, 27, 28)
Integer = NDArray[np.int64]


def decode(states: NDArray[np.uint64], wires: tuple[int, ...]) -> Integer:
    word = np.zeros(len(states), dtype=np.int64)
    for bit, wire in enumerate(wires):
        word |= (((states >> np.uint64(wire)) & 1).astype(np.int64)) << bit
    return word


def fit_lane(states: NDArray[np.uint64], normal: Integer, raw: Integer, scale: Integer,
             groups: list[Integer], mode: str, degree: int, remainder_bits: int) -> tuple[NDArray[np.uint64], list]:
    scaled_word = raw >> (13 - remainder_bits)
    divisor = 1 << remainder_bits
    half = divisor // 2
    shifts = np.asarray({"bits": LINEAR_WIRES, "word": (), "word-and-low": LOW_WIRES}[mode], dtype=np.uint64)
    combined = None if mode == "bits" else (decode(states, WORD_WIRES) ^ 1) - 1
    combined_scale = 1 << len(WORD_WIRES)
    feature_mask = np.uint64(sum(1 << wire for wire in LINEAR_WIRES))
    normalized_phase = np.empty(len(states), dtype=np.int64)
    tables = []
    for group in groups:
        if not len(group):
            raise ValueError("Missing root cell on the legal domain")
        # Keep every distinct pair of normalized input and observed bits.
        # Dropping rare representations can leave affine terms unidentified.
        keys = ((states[group] & feature_mask) << np.uint64(22)) | normal[group].astype(np.uint64)
        _, first = np.unique(keys, return_index=True)
        train = group[first]
        bits = ((states[train, None] >> shifts) & 1).astype(np.float64)
        linear = bits if combined is None else np.column_stack((combined[train] / combined_scale, bits))
        z = scaled_word[train] / divisor
        design = np.column_stack((np.ones(len(train)), linear, *(z**p for p in range(2, degree + 1))))
        response = 1024 / np.sqrt(normal[train])
        coefficients = np.rint(np.linalg.lstsq(design, response, rcond=1e-10)[0] * (1 << FRACTION)).astype(np.int64)
        if np.max(np.abs(coefficients)) >= 1 << 43:
            raise ValueError("Coefficient does not fit the checked integer evaluator")
        tables.append(coefficients.tolist())
        values = ((states[group, None] >> shifts) & 1).astype(np.int64)
        word = scaled_word[group]
        offset = 1 + linear.shape[1]
        start = 1
        if combined is not None:
            start += 1
        correction = np.full(len(group), coefficients[-1], dtype=np.int64)
        for coefficient in coefficients[offset:-1][::-1]:
            correction = ((correction * word + half) >> remainder_bits) + coefficient
        correction = (correction * word + half) >> remainder_bits
        correction = (correction * word + half) >> remainder_bits
        if combined is not None:
            correction += (coefficients[1] * combined[group] + combined_scale // 2) // combined_scale
        normalized_phase[group] = coefficients[0] + values @ coefficients[start:offset] + correction
    phase = normalized_phase.astype(np.uint64) << (64 - FRACTION - 10 + scale).astype(np.uint64)
    return phase, tables


def run(assembly: Path, simulator: Path, output: Path) -> None:
    if sha256(assembly) != CONTROL or sha256(simulator) != SIMULATOR:
        raise ValueError("Wrong pinned assembly or simulator")
    spec = spec_from_file_location("pinned_joint_simulator", simulator)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load the pinned simulator")
    km = module_from_spec(spec)
    spec.loader.exec_module(km)
    ops, register = km.parse_kmx(assembly)
    verify_rotation_prefix(ops, {CUT})
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {"assembly_sha256": CONTROL, "simulator_sha256": SIMULATOR,
        "driver_sha256": sha256(Path(__file__)), "prefix_end": CUT, "legal_inputs": MAX_X,
        "root_wires_lsb_first_with_low_bit_inverted": ROOT_WIRES, "exponent_wires_lsb_first": SCALE_WIRES,
        "remainder_wires_lsb_first": REMAINDER_WIRES, "affine_wires": LINEAR_WIRES,
        "coefficient_fraction_bits": FRACTION, "fit": "least squares over all distinct normalized input and affine-bit pairs",
        "combined_word_lsb_first_with_lsb_complemented_then_subtract_one": WORD_WIRES,
        "additional_low_wires": LOW_WIRES, "mode_degree_and_remainder_bits": FORMATS})
    sim = km.Sim(39, "zero")
    sim.load_x(register)
    sim.run([op for op in ops if op.line <= CUT])
    states = np.zeros(MAX_X, dtype=np.uint64)
    for wire in set(LINEAR_WIRES + ROOT_WIRES + SCALE_WIRES):
        states |= km.unpack(sim.Q[wire])[:MAX_X].astype(np.uint64) << np.uint64(wire)
    xs = np.arange(1, MAX_X + 1, dtype=np.int64)
    scale = decode(states, SCALE_WIRES)
    expected_scale = 11 - np.searchsorted(np.array([4**k for k in range(11)]), xs, side="right")
    if not np.array_equal(scale, expected_scale):
        raise ValueError("The exponent decoding failed")
    normal = xs << (2 * scale)
    root = (decode(states, ROOT_WIRES) ^ 1) + 256
    if np.any((16 * root**2 > normal) | (normal >= 16 * (root + 1)**2)):
        raise ValueError("The root decoding failed")
    raw = decode(states, REMAINDER_WIRES)
    permutation = np.argsort(normal, kind="stable")
    boundaries = np.searchsorted(root[permutation], np.arange(257, 512))
    groups = np.split(permutation, boundaries)
    target, tolerance = beta_one_targets(xs)

    def targets(chunk: Integer):
        return target[chunk - 1], tolerance[chunk - 1]

    results = []
    for mode, degree, width in FORMATS:
        phase, tables = fit_lane(states, normal, raw, scale, groups, mode, degree, width)
        path = output / f"{mode}-degree-{degree}-bits-{width}.json"
        write_json(path, tables)
        result = scan_phase(lambda chunk: phase[chunk - 1], MAX_X, targets)
        print(mode, degree, width, result["failed_inputs"], result["worst_tolerance_fraction"], flush=True)
        results.append({"mode": mode, "degree": degree, "remainder_bits": width,
                        "coefficient_sha256": sha256(path), **result})
    write_json(output / "screen.json", {"registration_sha256": sha256(registration),
        "scope": "exact fixed-point numerical phase, reversible emission and cost open",
        "root_and_exponent_decode_verified_inputs": MAX_X, "root_cells": 256, "lanes": results})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "simulator", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
