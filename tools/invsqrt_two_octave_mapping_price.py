"""Native resource measurement for the in-place two-octave address mapping."""

import json

from invsqrt_opportunity import backend, counts

from qcompile.invsqrt.two_octave_mapping import permute_address


def main() -> None:
    km, _, _ = backend()
    builder = km.CircuitBuilder()
    x = builder.create_quantum_register(22, "x")
    permute_address(builder, x, 7)
    permute_address(builder, x, 7, inverse=True)
    circuit = builder.finish_circuit()
    print(json.dumps({"mapping_and_restore_counts": counts(circuit.operation_statistics()),
                      "declared_qubits": circuit.num_qubits,
                      "persistent_extra_qubits": 0}, indent=2))


if __name__ == "__main__":
    main()
