"""Canonical serialization, immutable identities, and bounded safe extraction."""

import io
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np

from .errors import ValidationError
from .io import sha256

EPOCH = (1980, 1, 1, 0, 0, 0)


def _name(name):
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or ":" in name
        or path.is_absolute()
        or any(p in ("", ".", "..") for p in name.split("/"))
        or str(path) != name
    ):
        raise ValidationError(f"unsafe archive path: {name!r}")
    return name


def validate_layout(names):
    names = list(names)
    if len(names) != len(set(names)):
        raise ValidationError("duplicate archive member")
    for name in names:
        _name(name)
    fixed = {"invsqrt.kmb", "dqi.kmb", "dfthcsos/submission.npz"}
    angles = [name for name in names if re.fullmatch(r"dfthcsos/angle_k_(0|[1-9][0-9]*)\.kmb", name)]
    if not angles or set(names) != fixed | set(angles):
        raise ValidationError(
            "archive must have canonical binary circuits and factorization, with no extra paths"
        )
    if set(angles) != {f"dfthcsos/angle_k_{i}.kmb" for i in range(len(angles))}:
        raise ValidationError("angle indices must be contiguous from zero")


def zip_info(name):
    item = zipfile.ZipInfo(_name(name), EPOCH)
    item.create_system = 3
    item.external_attr = (stat.S_IFREG | 0o644) << 16
    item.compress_type = zipfile.ZIP_STORED
    return item


def deterministic_npz(path, arrays):
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) for key in arrays):
        raise ValidationError("invalid NPZ array name")
    with zipfile.ZipFile(path, "x") as archive:
        for key in sorted(arrays):
            array = np.asarray(arrays[key])
            if array.dtype.kind not in "fiu" or array.dtype.names or array.dtype.subdtype:
                raise ValidationError("NPZ requires plain real numeric arrays")
            if not np.isfinite(array).all():
                raise ValidationError("NPZ arrays must be finite")
            array = np.asarray(array, dtype=array.dtype.newbyteorder("<"), order="C")
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, array, version=(1, 0), allow_pickle=False)
            archive.writestr(zip_info(key + ".npy"), buffer.getvalue())


def manifest(root: Path, *, origin: str, provenance: str):
    if origin not in ("generated", "retained_reference") or not provenance:
        raise ValidationError("explicit artifact origin/provenance is required")
    root = Path(root)
    files = sorted(p for p in root.rglob("*") if p.is_file())
    names = [p.relative_to(root).as_posix() for p in files]
    validate_layout(names)
    result = {}
    for path, name in zip(files, names, strict=True):
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or path.stat().st_nlink != 1:
            raise ValidationError("artifact must be a regular file, not a link")
        result[name] = {
            "path": str(path.resolve()),
            "sha256": sha256(path),
            "origin": origin,
            "provenance": provenance,
        }
    return result


def validate_manifest(artifacts):
    validate_layout(artifacts)
    for name, record in artifacts.items():
        path = Path(record["path"])
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_nlink != 1
            or any(p.is_symlink() for p in path.parents)
        ):
            raise ValidationError(f"artifact missing or linked: {name}")
        if record.get("origin") not in ("generated", "retained_reference") or not record.get("provenance"):
            raise ValidationError(f"artifact provenance missing: {name}")
        if sha256(path) != record.get("sha256"):
            raise ValidationError(f"artifact bytes changed: {name}")


def hashes(artifacts):
    return {name: record["sha256"] for name, record in artifacts.items()}


def deterministic_zip(path, files):
    validate_layout(files)
    with zipfile.ZipFile(path, "x", allowZip64=True) as archive:
        for name in sorted(files):
            source = Path(files[name])
            if not source.is_file() or source.is_symlink():
                raise ValidationError(f"missing regular archive input: {name}")
            with source.open("rb") as src, archive.open(zip_info(name), "w", force_zip64=True) as dest:
                shutil.copyfileobj(src, dest, 1 << 20)


def extract_archive(path, destination, *, expected=None, max_bytes=8 << 30):
    """Validate every member before writing anything; extraction requires a new directory."""
    destination = Path(destination)
    if destination.exists():
        raise ValidationError("extraction directory must not exist")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        validate_layout(names)
        total = 0
        for item in infos:
            mode = item.external_attr >> 16
            if item.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG) or item.flag_bits & 1:
                raise ValidationError("archive contains a link, special, directory, or encrypted member")
            total += item.file_size
            if total > max_bytes:
                raise ValidationError("archive exceeds extraction byte limit")
        if expected is not None and set(expected) != set(names):
            raise ValidationError("archive paths differ from manifest")
        destination.mkdir(parents=True)
        for item in infos:
            target = destination / item.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as src, target.open("xb") as dest:
                shutil.copyfileobj(src, dest, 1 << 20)
            if expected is not None and sha256(target) != expected[item.filename]:
                raise ValidationError(f"extracted bytes differ: {item.filename}")
    return {name: sha256(destination / name) for name in sorted(names)}
