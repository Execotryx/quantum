"""NPZ v1.0 schema pinned to metric notebook v10, with bounded allocation."""

import math
import zipfile
from pathlib import Path

import numpy as np

from qcompile.errors import ValidationError

SPEC = {
    "U": ("f", ("R", "B", 76)),
    "W": ("f", ("R", "B", "C")),
    "H2_I": ("f", ("R", "C")),
    "H1_I": ("f", ()),
    "Hsym_lower": ("f", (2926,)),
    "tree_edges": ("iu", (75, 2)),
}
MAX_NPZ_BYTES = 2**26


def read_factorization(path: Path, spec=None, max_bytes=MAX_NPZ_BYTES):
    spec = SPEC if spec is None else spec
    dimensions, total = {}, 0
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {key + ".npy" for key in spec}:
            raise ValidationError("NPZ must contain exactly one member for each required array")
        for key, (kinds, expected) in spec.items():
            with archive.open(key + ".npy") as stream:
                if np.lib.format.read_magic(stream) != (1, 0):
                    raise ValidationError(f"{key}: expected NPY format 1.0")
                shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
            if dtype.kind not in kinds or dtype.names or dtype.subdtype or dtype.byteorder == ">":
                raise ValidationError(f"{key}: invalid plain numeric dtype")
            if len(shape) != len(expected):
                raise ValidationError(f"{key}: invalid shape")
            for actual, target in zip(shape, expected, strict=True):
                size = dimensions.setdefault(target, actual) if isinstance(target, str) else target
                if actual <= 0 or actual != size:
                    raise ValidationError(f"{key}: inconsistent shape/dimension")
            size = math.prod(shape) * dtype.itemsize
            total += size
            if total > max_bytes:
                raise ValidationError("NPZ allocation exceeds byte limit")
            # Prevent truncated/oversized payloads hidden behind valid headers.
            info = archive.getinfo(key + ".npy")
            if info.file_size > max_bytes + 10000 or info.file_size < size:
                raise ValidationError(f"{key}: inconsistent NPY payload size")
    with np.load(path, allow_pickle=False) as archive:
        arrays = {key: np.array(archive[key]) for key in spec}
    if any(not np.isfinite(value).all() for value in arrays.values()):
        raise ValidationError("non-finite NPZ array")
    return arrays
