"""Price marked stages of the exact banked and homogeneous D4 controls."""

import argparse
import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from dqi_phase_profile import load_decoder

from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend
from qcompile.vendored.dqi_d4 import homogeneous_groups


class StageBuilder:
    """Expose the source builder while measuring its top-level marks."""

    def __init__(self, builder):
        self.builder = builder
        self.depth = 0
        self.previous = 0
        self.stages = {}

    def __getattr__(self, name):
        return getattr(self.builder, name)

    @contextmanager
    def mark(self, name):
        self.depth += 1
        try:
            with self.builder.mark(name):
                yield
            if self.depth == 1:
                circuit = self.builder.finish_circuit()
                count = circuit.operation_statistics().num_toffoli_like
                if name in self.stages:
                    raise ValueError(f"Duplicate decoder stage: {name}")
                self.stages[name] = count - self.previous
                self.previous = count
        finally:
            self.depth -= 1


def profile(component: Path, backend: Path, controls: Path, output: Path) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    pins = read_json(controls)
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    source_manifest = component / "SOURCE.json"
    if inventory != pins["backend_inventory_sha256"] or (
        sha256(source_manifest) != pins["evidence_sha256"]["third_party/dqi-d4/SOURCE.json"]
    ):
        raise ValueError("D4 profiling sources differ from the frozen control inventory")
    for record in read_json(source_manifest)["files"]:
        if sha256(component / record["path"]) != record["sha256"]:
            raise ValueError(f"D4 source changed: {record['path']}")

    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    km = importlib.import_module("kickmix")
    # Keep the exact metadata order used by the banked and ablation builds.
    metadata = []
    for kind, label, count, start in (("q", "S", 70, 0), ("b", "E", 4095, 70)):
        for index in range(count):
            register = start + index
            metadata.append(f'REGISTER r{register} "{label}{index}"')
            metadata.extend(f"APPEND_TO_REGISTER {kind}{12 * index + bit} r{register}" for bit in range(12))

    reports = {}
    for role, groups in (("banked", ()), ("homogeneous", tuple(range(1, 8)))):
        module = load_decoder(component / "src", km)
        builder = StageBuilder(km.CircuitBuilder())
        syndrome = [builder.alloc_qubits(12) for _ in range(70)]
        masks = [builder.alloc_bits(12) for _ in range(4095)]
        with homogeneous_groups(module, groups):
            module.decode(builder, syndrome, masks)
        circuit = km.Circuit("\n".join(metadata)) + builder.finish_circuit()
        with TemporaryDirectory(dir=output.parent) as directory:
            kmb = Path(directory) / "decoder.kmb"
            circuit.to_file(str(kmb), format="kmb")
            digest = sha256(kmb)
        total = circuit.operation_statistics().num_toffoli_like
        if digest != pins["circuits"][role] or sum(builder.stages.values()) != total:
            raise ValueError(f"Profile did not cover the exact {role} control")
        reports[role] = {
            "sha256": digest, "qubits": circuit.num_qubits,
            "static_toffoli_like": total, "static_by_stage": builder.stages,
        }
        print(f"{role} profile matched: {digest}", flush=True)
        del circuit, builder
    write_json(output, {
        "controls_sha256": sha256(controls), "source_sha256": sha256(source_manifest),
        "backend_inventory_sha256": inventory, "driver_sha256": sha256(Path(__file__)), "reports": reports,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("component", "backend", "controls", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    profile(args.component, args.backend, args.controls, args.output)


if __name__ == "__main__":
    main()
