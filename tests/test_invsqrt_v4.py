import hashlib
from importlib import import_module

import pytest


@pytest.mark.official
def test_v4_frozen_lattice_rebuild(monkeypatch, project_root, tmp_path):
    pytest.importorskip("resource")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    config = tool.read_json(tool.CONFIG_V4)
    km, primitives, _ = tool.backend()
    circuit, _, _ = tool.direct_candidate(km, primitives, config["combined_lattice"])
    output = tmp_path / "candidate.kmb"
    circuit.to_file(str(output), format="kmb")
    assert hashlib.sha256(output.read_bytes()).hexdigest() == config["frozen_sha256"]["combined-lattice"]
