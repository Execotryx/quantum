#!/usr/bin/env python3
"""Supplement check-submission with NPZ header bounds and ANGLE T counts."""
import json
import math
from pathlib import Path
import sys
import zipfile

import kickmix as km
import numpy as np

root = Path(sys.argv[1]) / "dfthcsos"
audit = {"npz_headers": {}, "angle_circuits": {}}
with zipfile.ZipFile(root / "submission.npz") as z:
    for member in z.infolist():
        with z.open(member) as f:
            version = np.lib.format.read_magic(f)
            assert version == (1, 0), (member.filename, version)
            shape, _, dtype = np.lib.format.read_array_header_1_0(f)
        assert dtype.kind in ("f", "i", "u") and dtype.byteorder != ">"
        assert dtype.names is None and dtype.subdtype is None
        audit["npz_headers"][member.filename] = {
            "shape": list(shape), "dtype": dtype.str,
            "array_bytes": math.prod(shape) * dtype.itemsize,
            "npy_version": list(version),
        }
audit["total_npz_array_bytes"] = sum(x["array_bytes"] for x in audit["npz_headers"].values())
assert audit["total_npz_array_bytes"] <= 2**26
for p in sorted(root.glob("angle_k_*.kmb")):
    circuit = km.Circuit.from_file(str(p))
    stats = circuit.operation_statistics()
    audit["angle_circuits"][p.name] = {
        "num_qubits": circuit.num_qubits, "num_bits": circuit.num_bits,
        "registers": list(circuit.register_data), "t_gates": int(stats.num_t_like),
        "static_toffolis": int(stats.num_toffoli_like),
    }
    assert stats.num_t_like == 0 and circuit.num_qubits <= 128
print(json.dumps(audit, indent=2))
