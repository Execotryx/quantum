"""Versioned score and lineage bindings for the complete portfolio."""

import re
from fractions import Fraction
from math import prod
from pathlib import Path

from .artifacts import validate_layout
from .component_confirmations import BENCHMARKS, component_hashes
from .io import read_json, sha256

ABOVE_34 = "portfolio-v2"
ABOVE_36 = "portfolio-v3"
ABOVE_35 = "portfolio-v4"
AT_LEAST_35 = "portfolio-v5"
VERSIONED_FORMATS = {34: ABOVE_34, 35: ABOVE_35, 36: ABOVE_36}


def is_digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def clears_target(score: float, target: int, baselines: dict, costs: dict, *, inclusive: bool = False) -> bool:
    """Check the exact cost-product inequality after the numeric score calculation."""
    if (inclusive and target != 35) or (not inclusive and score <= target):
        return False
    if target not in (35, 36):
        return True
    baseline_product = prod(map(Fraction, baselines.values()))
    scaled_cost = target**3 * prod(map(Fraction, costs.values()))
    return baseline_product >= scaled_cost if inclusive else baseline_product > scaled_cost


def portfolio_target(record: dict) -> int:
    if "format" not in record and "minimum_score" not in record and "components" not in record:
        return 20
    target = record.get("minimum_score")
    if type(target) is not int or target not in VERSIONED_FORMATS:
        raise ValueError("Unsupported portfolio registration or score target")
    actual_format = record.get("format")
    if actual_format != VERSIONED_FORMATS[target] and (target, actual_format) != (35, AT_LEAST_35):
        raise ValueError("Unsupported portfolio registration or score target")
    components = record.get("components")
    if not isinstance(components, dict) or set(components) != set(BENCHMARKS):
        raise ValueError("Exactly three component lineage records are required")
    members = record.get("artifact_hashes")
    if not isinstance(members, dict) or not all(is_digest(digest) for digest in members.values()):
        raise ValueError("Invalid portfolio member digests")
    validate_layout(members)
    for name, component in components.items():
        if not isinstance(component, dict):
            raise ValueError(f"Invalid {name} lineage")
        source = component.get("source_sha256")
        builds = component.get("build_receipt_sha256")
        if (
            not isinstance(builds, list) or len(builds) != 2 or builds[0] == builds[1]
            or not all(is_digest(digest) for digest in [source, *builds])
            or component.get("members") != component_hashes(members, name)
        ):
            raise ValueError(f"Invalid {name} lineage or build receipt binding")
    return target


def bind_lineage(path: Path, members: dict[str, str], *, minimum_score: int = 34, inclusive: bool = False) -> dict:
    """Pin reviewed source manifests and build receipts to the supplied member hashes."""
    if minimum_score not in VERSIONED_FORMATS or (inclusive and minimum_score != 35):
        raise ValueError("Unsupported portfolio registration or score target")
    declarations = read_json(path)
    if not isinstance(declarations, dict) or set(declarations) != set(BENCHMARKS):
        raise ValueError("Lineage must cover exactly the three benchmarks")
    components = {}
    for name, declaration in declarations.items():
        if (
            not isinstance(declaration, dict) or not isinstance(declaration.get("source"), str)
            or not isinstance(declaration.get("builds"), list) or len(declaration["builds"]) != 2
            or any(not isinstance(build, str) for build in declaration["builds"])
        ):
            raise ValueError(f"{name} requires a source manifest and two build receipts")
        source = sha256(path.parent / declaration["source"])
        expected = component_hashes(members, name)
        receipts = []
        for build in declaration["builds"]:
            receipt = path.parent / build
            digest = sha256(receipt)
            record = read_json(receipt)
            if record.get("source_sha256") != source or record.get("members") != expected:
                raise ValueError(f"{name} build receipt differs from the source or members")
            if sha256(receipt) != digest:
                raise ValueError(f"{name} build receipt changed during registration")
            receipts.append(digest)
        components[name] = {
            "source_sha256": source,
            "build_receipt_sha256": receipts,
            "members": expected,
        }
    binding = {"format": AT_LEAST_35 if inclusive else VERSIONED_FORMATS[minimum_score],
               "minimum_score": minimum_score, "components": components}
    portfolio_target({**binding, "artifact_hashes": members})
    return binding
