"""Compare a tower-field EEA decoder with the pinned polynomial-field control."""

import argparse
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

from qcompile.dqi.tower import multiply_xor
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


class TowerBuilder:
    """Delegate the pinned schedule and replace its two controlled product sites."""

    def __init__(self, builder: Any):
        self.builder = builder

    def __getattr__(self, name: str) -> Any:
        return getattr(self.builder, name)

    def ixor_gf2_mul(self, left, right, *, target, field, control):
        if field.degree != 12:
            raise ValueError("tower decoder requires GF(4096)")
        masked = self.builder.alloc_qubits(field.degree)
        for src, dst in zip(left, masked, strict=True):
            self.builder.init_and(control, src, dst)
        multiply_xor(self.builder, masked, right, target)
        for src, dst in zip(left, masked, strict=True):
            self.builder.del_and(control, src, dst)
        self.builder.free(masked)


def compare(backend_path: Path, output: Path, *, m: int, n: int, seed: int) -> None:
    if not 2 <= n <= min(m, 70) or n % 2 or m > 4095:
        raise ValueError("require even syndrome count in [2, 70] and n <= m <= 4095")
    settings = read_json(backend_path)
    validate_backend(settings)
    official = Path(settings["verifiers_root"]) / "dqi"
    sys.path[:0] = [settings["kickmix_root"], str(official)]
    km = import_module("kickmix")
    ref = import_module("dqi_reference_circuit")
    verifier = import_module("verify_submission_dqi")
    shots = 2560
    spec = verifier.ProblemSpecDQI.benchmark_instance(m=m, n=n, degree=12, num_shots=shots)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {
        "scope": "development only", "m": m, "n": n, "degree": 12, "seed": seed,
        "shots": shots, "backend": settings,
        "emitter_sha256": sha256(official / "dqi_reference_circuit.py"),
        "verifier_sha256": sha256(official / "verify_submission_dqi.py"),
    })

    for name in ("reference", "tower"):
        if name == "reference":
            circuit = ref.build_reference_circuit(m, n, 12)
        else:
            builder = TowerBuilder(km.CircuitBuilder())
            syndromes = [builder.create_quantum_register(12, name=f"S{i}") for i in range(n)]
            error_mbuc = [builder.create_classical_register(12, name=f"E{j}") for j in range(m)]
            ref.ProosAndZalkaDecoder(n, km.GF2Field(12)).build_syndrome_decoding_mbuc(
                builder, syndromes=syndromes, error_mbuc=error_mbuc, n_iters=ref.default_n_iters(n),
            )
            circuit = builder.finish_circuit()
            del builder
        path = output / f"{name}.kmb"
        with path.open("xb") as stream:
            circuit.to_file(stream, format="kmb")
        del circuit
        circuit = km.Circuit.from_file(str(path))
        result = verifier.verify(circuit, spec, seed=seed, batch_size=256, max_workers=1)
        write_json(output / f"{name}.json", {**result, "kmb_sha256": sha256(path)})
        del circuit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--m", type=int, default=63)
    parser.add_argument("--n", type=int, default=4)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    compare(args.backend, args.output, m=args.m, n=args.n, seed=args.seed)
