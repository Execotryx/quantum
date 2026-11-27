"""Price necessary chemistry resource budgets with the pinned PREPARE model."""

import argparse
from decimal import Decimal
from importlib import import_module
from pathlib import Path
import sys
from typing import Any

import numpy as np

from qcompile.io import sha256, write_json


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "vendor" / "official" / "verifiers"
MODEL_SHA256 = "7f1e190c42fc5325f3e6689fbbef51f95b0cb12f1c828cda92b6c088e72206da"
CONTROL_SHA256 = "92554e09cf2ce4a1ab86c53b4948f8ece503df972fe3e01824b58bb64361b0e0"
# Round the analytical floor downward so every allowance is optimistic.
NORMALIZATION_FLOOR = Decimal("46.78617")
CHEMISTRY_LIMITS = {"joint": Decimal("230000000"), "measured_companions": Decimal("212762708.586")}
SHAPES = ((9, 127, 46), (9, 127, 40), (9, 119, 46), (9, 96, 46), (9, 95, 46), (9, 63, 46),
          (8, 127, 42), (8, 120, 40), (9, 143, 40), (9, 129, 40), (10, 129, 40))


def budget(factory: Any, shape: tuple[int, int, int], batch: int, brot: int) -> dict[str, Any]:
    r, b, c = shape
    model = factory(R=r, B=b, C=c, N=76, chi=10, beta=brot)
    outer = model.outer_state_prep_qubit_cost()
    inner = model.inner_state_prep_qubit_cost()
    addresses = 76 + r * b
    address_bits = (addresses - 1).bit_length()
    persistent = outer["persistent"] + inner["persistent"] + batch * brot
    heuristic_temp = max(outer["temporary"], inner["temporary"])
    loader_temp_max = 128 - address_bits - batch * brot
    if loader_temp_max < 0:
        raise ValueError("The batch leaves no legal ANGLE layout")
    width = persistent + heuristic_temp
    fixed = model.outer_state_prep() + model.inner_state_prep() + model.givens_rotations()
    allowance = {key: float((limit / (NORMALIZATION_FLOOR * width) - fixed) / 2)
                 for key, limit in CHEMISTRY_LIMITS.items()}
    return {
        "shape": shape, "batch": batch, "brot": brot, "legal_addresses": addresses,
        "angle_family_size": (75 + batch - 1) // batch, "selection_qubits": address_bits,
        "max_loader_temporary_under_cap": loader_temp_max, "heuristic_temporary": heuristic_temp,
        "minimum_task_qubits": width, "fixed_toffolis": fixed,
        "optimistic_angle_toffolis_per_pass": allowance,
        "projected_cost_at_v222_loader_charge": float(NORMALIZATION_FLOOR * width * (fixed + 6610)),
    }


def exact_duplicate_inventory(factorization: Path) -> list[dict[str, int]]:
    with np.load(factorization, allow_pickle=False) as source:
        weights = source["W"]
        words = source["angle_words"]
    groups, bases, _ = weights.shape
    if words.shape != (76 + groups * bases, 75):
        raise ValueError("The pinned angle table does not match the factorization")
    blocks = words[76:].reshape(groups, bases, 75)
    result = []
    for weight, block in zip(weights, blocks, strict=True):
        active = np.any(weight != 0, axis=1)
        active_count = int(np.count_nonzero(active))
        distinct = len(np.unique(block[active], axis=0))
        result.append({"zero_weight_rows": bases - active_count, "duplicate_active_word_rows": active_count - distinct})
    return result


def run(factorization: Path, output: Path) -> None:
    source = OFFICIAL / "dfthcsos" / "scoreinfra" / "costs_prepare.py"
    if sha256(source) != MODEL_SHA256 or sha256(factorization) != CONTROL_SHA256:
        raise ValueError("Unexpected model or factorization")
    sys.path.insert(0, str(OFFICIAL))
    model = import_module("dfthcsos.scoreinfra.costs_prepare")
    if Path(model.__file__ or "").resolve() != source:
        raise ValueError("The imported cost model is not the pinned source")
    control = budget(model.SpinFreeData_V1, SHAPES[0], 5, 7)
    if (control["minimum_task_qubits"], control["fixed_toffolis"]) != (405, 6500):
        raise ValueError("Failed to reproduce the v222 control resource breakdown")
    candidates = [budget(model.SpinFreeData_V1, shape, batch, 7)
                  for shape in SHAPES for batch in (1, 3, 5, 7)]
    write_json(output, {
        "scope": "optimistic PREPARE and ANGLE budget, plus exact zero-weight or identical-word inventory",
        "driver_sha256": sha256(Path(__file__)), "cost_model_sha256": MODEL_SHA256,
        "factorization_sha256": CONTROL_SHA256, "normalization_floor": str(NORMALIZATION_FLOOR),
        "chemistry_limits": {key: str(value) for key, value in CHEMISTRY_LIMITS.items()},
        "control_duplicate_inventory": exact_duplicate_inventory(factorization), "resource_rows": candidates,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("factorization", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
