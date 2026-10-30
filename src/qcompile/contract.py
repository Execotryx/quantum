"""Provenance-aware contracts. Report-derived values never count as reconciled."""

from dataclasses import dataclass
from pathlib import Path

from .errors import BlockedError, ValidationError
from .io import identity, read_json, sha256

REQUIRED_FIELDS = frozenset(
    {
        "invsqrt.domain",
        "invsqrt.input_bits",
        "invsqrt.phase_accumulator_bits",
        "invsqrt.trajectories_per_input",
        "invsqrt.tolerance_relative_turns",
        "invsqrt.rotation_price",
        "invsqrt.accumulator_rounding",
        "invsqrt.circuit_rotation_encoding",
        "dqi.parameters",
        "dqi.modulus",
        "dqi.shots",
        "dqi.delta",
        "dqi.weight_distribution",
        "dqi.classical_binding",
        "chemistry.orbitals",
        "chemistry.electrons",
        "chemistry.residual_bound",
        "chemistry.fixed_symmetry",
        "chemistry.energy_upper",
        "chemistry.full_cost_accounting",
        "chemistry.angle_units",
        "chemistry.tree_root_and_order",
        "chemistry.one_electron_matching",
        "chemistry.unused_address_behavior",
        "chemistry.npz_schema",
        "runtime_limits",
        "baseline.acceptance",
        "baseline.component_profiles",
        "competition.open_status",
        "correctness.primitive_composition_evidence",
        "archive.encoding",
        "preflight.allowed_instructions",
        "preflight.max_npz_bytes",
        "preflight.max_qubit_or_bit_id",
        "release.coverage",
    }
)


@dataclass(frozen=True)
class Contract:
    data: dict

    @property
    def hash(self):
        return identity(self.data)

    def blockers(self, root: Path) -> list[str]:
        problems = []
        if self.data.get("schema_version") != 1:
            problems.append("unsupported contract schema")
        for name in sorted(REQUIRED_FIELDS - self.data.get("fields", {}).keys()):
            problems.append(f"missing required contract field: {name}")
        for name, field in self.data.get("fields", {}).items():
            if field.get("release_critical", True) and field.get("status") != "reconciled":
                problems.append(f"unresolved contract field: {name}")
            if field.get("value") is None:
                problems.append(f"missing contract value: {name}")
            if name in REQUIRED_FIELDS and field.get("release_critical") is not True:
                problems.append(f"required contract field cannot be optional: {name}")
            if field.get("status") == "reconciled":
                source = field.get("official") or {}
                path = root / source.get("path", "")
                if not source.get("location") or not path.is_file() or sha256(path) != source.get("sha256"):
                    problems.append(f"missing or changed official provenance: {name}")
        for key in ("valid_inputs", "initialization", "measurements", "composition", "unused_addresses"):
            if not self.data.get("correctness_scope", {}).get(key):
                problems.append(f"undeclared correctness assumption: {key}")
        for item in self.data.get("discrepancies", []):
            if item.get("release_critical", True) and item.get("status") != "resolved":
                problems.append(f"open discrepancy: {item['id']}")
        for role in ("rules", "data", "evaluation", "metric", "starter_kit", "reference", "paper", "backend"):
            source = self.data.get("sources", {}).get(role, {})
            path = root / source.get("path", "")
            if not source.get("origin") or not path.is_file() or sha256(path) != source.get("sha256"):
                problems.append(f"unpinned source: {role}")
        if not self.data.get("fields"):
            problems.append("contract contains no fields")
        return problems

    def require_ready(self, root: Path):
        problems = self.blockers(root)
        if problems:
            raise BlockedError("G0 contract blocked:\n" + "\n".join(problems))


def load_contract(path) -> Contract:
    data = read_json(Path(path))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValidationError("expected contract schema_version 1")
    if not isinstance(data.get("fields"), dict):
        raise ValidationError("contract fields must be an object")
    for name, field in data["fields"].items():
        if field.get("status") not in ("unresolved", "report_derived", "reconciled"):
            raise ValidationError(f"invalid provenance status: {name}")
    return Contract(data)
