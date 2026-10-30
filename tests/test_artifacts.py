import stat
import zipfile

import pytest

from qcompile.artifacts import deterministic_zip, extract_archive, hashes, validate_layout, zip_info
from qcompile.errors import ValidationError

NAMES = ["invsqrt.kmb", "dqi.kmb", "dfthcsos/angle_k_0.kmb", "dfthcsos/submission.npz"]


def test_deterministic_zip_extract_and_manifest(tmp_path, artifact_set):
    files = {name: item["path"] for name, item in artifact_set.items()}
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    deterministic_zip(a, files)
    deterministic_zip(b, dict(reversed(list(files.items()))))
    assert a.read_bytes() == b.read_bytes()
    observed = extract_archive(a, tmp_path / "extracted", expected=hashes(artifact_set))
    assert observed == hashes(artifact_set)
    with pytest.raises(ValidationError, match="must not exist"):
        extract_archive(a, tmp_path / "extracted")


@pytest.mark.parametrize(
    "names",
    [
        NAMES + ["../escape"],
        NAMES + ["/absolute"],
        NAMES + ["dfthcsos\\bad"],
        NAMES + ["invsqrt.kmx"],
        NAMES + ["dqi.kmb"],
        ["parent/" + name for name in NAMES],
        [n.replace("angle_k_0", "angle_k_1") for n in NAMES],
        NAMES + ["dfthcsos/angle_k_00.kmb"],
    ],
)
def test_layout_negative_controls(names):
    with pytest.raises(ValidationError):
        validate_layout(names)


@pytest.mark.parametrize("mutation", ["symlink", "directory", "duplicate", "oversize", "wrong_hash"])
def test_extraction_checks_everything_before_use(tmp_path, mutation):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name in NAMES:
            info = zip_info(name)
            if mutation == "symlink" and name == "dqi.kmb":
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            if mutation == "directory" and name == "dqi.kmb":
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
            archive.writestr(info, b"test-only")
        if mutation == "duplicate":
            with pytest.warns(UserWarning):
                archive.writestr("invsqrt.kmb", b"duplicate")
    args = {"max_bytes": 1} if mutation == "oversize" else {}
    if mutation == "wrong_hash":
        args["expected"] = dict.fromkeys(NAMES, "0" * 64)
    with pytest.raises(ValidationError):
        extract_archive(path, tmp_path / "extract", **args)
    assert not (tmp_path / "escape").exists()
