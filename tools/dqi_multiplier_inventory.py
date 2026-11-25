"""Inventory the field arithmetic emitted by the banked D4 decoder."""

import argparse
import importlib.util
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "third_party/dqi-d4/src"
SOURCE_PREFIX = f"{SOURCE}/"
QUANTUM_OPERANDS = {"init_and", "ccx", "ccz", "cswap"}
REGISTER_NAMES = ("x", "a", "p", "N")


@dataclass
class Call:
    key: tuple[str, str, str]
    start_live: int
    entry_condition: int
    peak_live: int
    unconditional_toffolis: int = 0
    conditional_toffolis: int = 0


class InventoryBuilder:
    def __init__(self, builder: Any, qubit: type) -> None:
        self.builder = builder
        self.qubit = qubit
        self.calls: dict[FrameType, Call] = {}
        self.records: dict[tuple[str, str, str], Counter[tuple[int, int, int, int, int]]] = defaultdict(Counter)
        self.condition_depth = 0
        self.peak_live = builder.num_allocated_qubits

    def __getattr__(self, name: str) -> Any:
        operation = getattr(self.builder, name)
        if name == "alloc_qubits":
            def allocate(*args: Any, **kwargs: Any) -> Any:
                result = operation(*args, **kwargs)
                live = self.builder.num_allocated_qubits
                self.peak_live = max(self.peak_live, live)
                for call in self.calls.values():
                    call.peak_live = max(call.peak_live, live)
                return result
            return allocate
        if name in {"push_condition", "pop_condition"}:
            def condition(*args: Any, **kwargs: Any) -> Any:
                self.condition_depth += 1 if name == "push_condition" else -1
                return operation(*args, **kwargs)
            return condition
        if name in QUANTUM_OPERANDS:
            def count(*args: Any, **kwargs: Any) -> Any:
                if self.calls and all(isinstance(wire, self.qubit) for wire in args):
                    for call in self.calls.values():
                        if self.condition_depth:
                            call.conditional_toffolis += 1
                        else:
                            call.unconditional_toffolis += 1
                return operation(*args, **kwargs)
            return count
        return operation

    def trace(self, frame: FrameType, event: str, _argument: object) -> None:
        if event == "return" and frame in self.calls:
            call = self.calls.pop(frame)
            variation = (call.unconditional_toffolis, call.conditional_toffolis,
                         call.peak_live - call.start_live, call.peak_live, call.entry_condition)
            self.records[call.key][variation] += 1
        if event != "call":
            return
        code = frame.f_code
        name = code.co_name
        if not code.co_filename.startswith(SOURCE_PREFIX):
            return
        if not any(term in name for term in ("mul", "inverse", "product", "quotient", "divide", "norm")):
            return
        arguments = frame.f_locals
        if arguments.get("b") is not self:
            return
        register = next((arguments.get(key) for key in REGISTER_NAMES if key in arguments), None)
        if register is None or not hasattr(register, "__len__") or len(register) != 12:
            return
        first = register[0]
        if not isinstance(first, self.qubit):
            return
        key = (str(Path(code.co_filename).relative_to(SOURCE)), name, "GF(2^12)")
        live = self.builder.num_allocated_qubits
        self.calls[frame] = Call(key, live, self.condition_depth, live)

    def inventory(self) -> list[dict[str, Any]]:
        return [
            {
                "source": source,
                "function": name,
                "field": field,
                "static_calls": sum(variants.values()),
                "unconditional_calls": sum(count for (*_, depth), count in variants.items() if depth == 0),
                "peak_live": max(variant[3] for variant in variants),
                "at_decoder_live_peak": any(variant[3] == self.peak_live for variant in variants),
                "variants": [
                    {"static_calls": count, "unconditional_toffolis": unconditional,
                     "conditional_toffolis": conditional, "extra_live_qubits": extra,
                     "peak_live_qubits": peak, "entry_condition_depth": depth}
                    for (unconditional, conditional, extra, peak, depth), count in sorted(variants.items())
                ],
            }
            for (source, name, field), variants in sorted(self.records.items())
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    backend = read_json(args.backend)
    validate_backend(backend)
    bank = read_json(ROOT / "docs/evidence/vendored-dqi/dqi-v8.json")
    manifest_file = SOURCE.parent / "SOURCE.json"
    if sha256(manifest_file) != bank["source_sha256"]:
        raise ValueError("D4 provenance differs from the banked member")
    for record in read_json(manifest_file)["files"]:
        if sha256(SOURCE.parent / record["path"]) != record["sha256"]:
            raise ValueError(f"D4 source changed: {record['path']}")

    sys.path.insert(0, backend["kickmix_root"])
    km = importlib.import_module("kickmix")
    sys.modules["circ"] = km
    spec = importlib.util.spec_from_file_location("decoder_under_test", SOURCE / "exp/r-main/stream/decode.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load D4 decoder")
    decoder = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = decoder
    spec.loader.exec_module(decoder)

    builder = km.CircuitBuilder()
    syndromes = [builder.alloc_qubits(12) for _ in range(70)]
    coefficients = [builder.alloc_bits(12) for _ in range(4095)]
    trace = InventoryBuilder(builder, km.q)
    sys.setprofile(trace.trace)
    try:
        decoder.decode(trace, syndromes, coefficients)
    finally:
        sys.setprofile(None)
    if trace.calls or trace.condition_depth:
        raise RuntimeError("D4 tracing ended with unclosed calls or condition scopes")

    # The metadata order and placement are part of the exact upstream build.
    metadata = []
    for index in range(70):
        metadata.append(f'REGISTER r{index} "S{index}"')
        metadata.extend(f"APPEND_TO_REGISTER q{12 * index + bit} r{index}" for bit in range(12))
    for index in range(4095):
        metadata.append(f'REGISTER r{70 + index} "E{index}"')
        metadata.extend(f"APPEND_TO_REGISTER b{12 * index + bit} r{70 + index}" for bit in range(12))
    circuit = km.Circuit("\n".join(metadata)) + builder.finish_circuit()
    args.output.mkdir(parents=True, exist_ok=True)
    circuit_path = args.output / "dqi-inventory-control.kmb"
    circuit.to_file(str(circuit_path), format="kmb")
    digest = sha256(circuit_path)
    if digest != bank["sha256"]:
        raise ValueError("Traced build differs from the exact banked D4 bytes")
    report = {
        "decoder_sha256": digest,
        "source_sha256": bank["source_sha256"],
        "backend_sha256": sha256(args.backend),
        "qubits": circuit.num_qubits,
        "static_toffolis": circuit.operation_statistics().num_toffoli_like,
        "peak_live_qubits": trace.peak_live,
        "primitives": trace.inventory(),
    }
    write_json(args.output / "inventory.json", report)


if __name__ == "__main__":
    main()
