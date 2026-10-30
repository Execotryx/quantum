"""Small deterministic records; no pickle, implicit NaN, or silent overwrite."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from .errors import ValidationError


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def identity(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def read_json(path: Path):
    def reject(value):
        raise ValidationError(f"non-finite JSON constant: {value}")

    return json.loads(Path(path).read_text(), parse_constant=reject)


def write_json(path: Path, value, *, replace=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(value)
    if not replace:
        with path.open("xb") as stream:
            stream.write(payload)
        return
    descriptor, temp = tempfile.mkstemp(dir=path.parent, prefix=".record-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def positive_int(value, name):
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{name} must be a positive integer")
    return value


def nonnegative_int(value, name):
    if type(value) is not int or value < 0:
        raise ValidationError(f"{name} must be a nonnegative integer")
    return value
