from pathlib import Path

import pytest

from qcompile.artifacts import manifest


@pytest.fixture
def artifact_set(tmp_path):
    root = tmp_path / "artifacts"
    for name in ("invsqrt.kmb", "dqi.kmb", "dfthcsos/angle_k_0.kmb", "dfthcsos/submission.npz"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("test fixture only, not a circuit: " + name).encode())
    return manifest(root, origin="generated", provenance="test-only synthetic bytes, never official evidence")


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parents[1]
