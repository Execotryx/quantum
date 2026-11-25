import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "third_party"
ADMISSION = {
    "explicit_license", "generating_source", "pinned_bytes", "no_competition_data", "not_denylisted",
}
DENIED_HASH_PREFIX = "993c70386a3d"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def test_project_license_matches_canonical_record() -> None:
    license_path = ROOT / "LICENSE"
    content = license_path.read_bytes()
    record = read(VENDOR / "licenses.json")["LICENSE"]
    assert content.lstrip().startswith(b"Apache License\n")
    assert b"Version 2.0, January 2004" in content
    assert b"END OF TERMS AND CONDITIONS" in content
    assert b"Copyright [yyyy] [name of copyright owner]" in content
    assert b"\r" not in content and not content.startswith(b"\xef\xbb\xbf")
    assert len(content) == record["bytes"]
    assert digest(license_path) == record["sha256"]
    assert record["source"]
    assert datetime.fromisoformat(record["retrieved_utc"]).utcoffset() is not None


def test_vendored_components_are_attributed_and_hash_pinned() -> None:
    root_notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    for component in sorted(path for path in VENDOR.iterdir() if path.is_dir()):
        assert not component.is_symlink()
        source = read(component / "SOURCE.json")
        assert isinstance(source["name"], str) and source["name"].strip()
        assert source["name"] in root_notice
        assert urlsplit(source["url"]).scheme == "https" and urlsplit(source["url"]).hostname
        assert isinstance(source["revision"], str) and source["revision"].strip()
        assert isinstance(source["authors"], list) and source["authors"]
        assert all(isinstance(author, str) and author.strip() for author in source["authors"])
        assert source["spdx"] == "Apache-2.0"
        assert datetime.fromisoformat(source["retrieved_utc"]).utcoffset() is not None
        assert set(source["admission"]) == ADMISSION
        for finding in source["admission"].values():
            assert finding["passed"] is True
            assert isinstance(finding["evidence"], str) and finding["evidence"].strip()

        paths = list(component.rglob("*"))
        assert not any(path.is_symlink() for path in paths)
        actual = {path.relative_to(component).as_posix() for path in paths if path.is_file()}
        files = source["files"]
        assert len({file["path"] for file in files}) == len(files)
        assert {file["path"] for file in files} == actual - {"SOURCE.json"}
        assert "LICENSE" in actual
        assert any(name.startswith("src/") and Path(name).suffix not in {".kmb", ".npz"} for name in actual)
        assert not any("/" in name and not name.startswith("src/") for name in actual)
        assert "jday96314" not in source["url"].casefold()
        for file in files:
            path = component / file["path"]
            assert path.stat().st_size == file["bytes"]
            assert digest(path) == file["sha256"]
            assert not file["sha256"].startswith(DENIED_HASH_PREFIX)
        outputs = source["published_outputs"]
        assert isinstance(outputs, list)
        assert len({output["name"] for output in outputs}) == len(outputs)
        for output in outputs:
            assert isinstance(output["name"], str) and output["name"].strip()
            assert re.fullmatch(r"[0-9a-f]{64}", output["sha256"])
            assert not output["sha256"].startswith(DENIED_HASH_PREFIX)


def test_vendored_tree_excludes_competition_assets() -> None:
    inventory = read(ROOT / "contracts" / "vendoring-exclusions.json")
    official_names = {name.casefold() for name in inventory["paths"]}
    hashes = set(inventory["sha256"])
    for path in VENDOR.rglob("*"):
        if not path.is_file() or path.name in {"LICENSE", "LICENSE.origin", "NOTICE"}:
            continue
        relative = PurePosixPath(path.relative_to(VENDOR).as_posix().casefold())
        assert not any(PurePosixPath(*relative.parts[i:]).as_posix() in official_names
                       for i in range(len(relative.parts))), path
        assert digest(path) not in hashes, path
