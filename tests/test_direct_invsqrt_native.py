"""Native mutation controls for the independently generated circuit."""

import subprocess
import sys
from functools import partial
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.official
def test_native_direct_phasing_mutations(monkeypatch, project_root, tmp_path):
    pytest.importorskip("resource")
    from fractions import Fraction

    from qcompile.invsqrt.direct import DirectFormat, build_circuit, coefficient_table, phase64

    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")

    if not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned backend unavailable")
    km, primitives, official = tool.backend()
    fmt = DirectFormat(3, 2, (13, 9, 5), fused=True, reuse_lookup=True)
    spec = official.ProblemSpecInvSqrt.for_n_p(fmt.n_p)
    points = list(range(1, spec.max_x + 1))
    policy = {"batch": 64, "repeat": 8, "seed": 443}
    table = coefficient_table(fmt)
    model = partial(phase64, fmt, table)
    names = ("_normalize", "_denormalize", "_add_row", "_phase_by_bits")
    api = {name: getattr(primitives, name) for name in names}
    original, _ = tool.emit(km, build_circuit(km, primitives, fmt, table), official, tmp_path / "direct.kmb")
    tool.native_smoke(km, official, original, spec, model, points, policy)

    c0, *rest = table[0]
    changed = ((c0 - 1, *rest), *table[1:])
    swapped = (table[1], table[0], *table[2:])
    for words in (changed, swapped):
        with pytest.raises(ValueError, match="phase mismatch"):
            tool.native_smoke(
                km, official, build_circuit(km, primitives, fmt, words), spec, model, points, policy
            )

    def sign(builder, output):
        for bit in range(len(output)):
            builder.z_pow(output[bit], -(Fraction(2) ** (bit - len(output) + 1)))

    phase_mutation = SimpleNamespace(**{**api, "_phase_by_bits": sign})
    with pytest.raises(ValueError, match="phase mismatch"):
        tool.native_smoke(
            km, official, build_circuit(km, phase_mutation, fmt, table), spec, model, points, policy
        )

    def incomplete_normalization(builder, inverse, x, flags):
        if not inverse:
            primitives._normalize(builder, inverse, x, flags)

    cleanup_mutation = SimpleNamespace(**{**api, "_normalize": incomplete_normalization})
    with pytest.raises(ValueError, match="input restoration"):
        tool.native_smoke(
            km, official, build_circuit(km, cleanup_mutation, fmt, table), spec, model, points, policy
        )

    class NonconstantCount:
        def __init__(self, **options):
            self.sim = km.Simulator(**options)

        def __getattr__(self, name):
            return getattr(self.sim, name)

        def operation_statistics(self):
            actual = self.sim.operation_statistics()
            return SimpleNamespace(
                num_toffoli_like=actual.num_toffoli_like + 1,
                num_t_like=actual.num_t_like,
                num_z_pow=actual.num_z_pow,
            )

    with pytest.raises(ValueError, match="executed counts differ"):
        tool.native_smoke(
            SimpleNamespace(Simulator=NonconstantCount), official, original, spec, model, points, policy
        )


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="requires Linux process sampling")
def test_direct_screen_resource_controls(monkeypatch, project_root, tmp_path):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    worker_dir = tmp_path / "worker"
    worker_dir.mkdir()
    child_file = worker_dir / "child.pid"
    worker = (
        "import subprocess,sys,time; from pathlib import Path; "
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(600)']); "
        "Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(600)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        tool.run_job([sys.executable, "-c", worker, str(child_file)], worker_dir, timeout=2)
    child_stat = Path(f"/proc/{int(child_file.read_text())}/stat")
    if child_stat.exists():
        assert child_stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    assert (worker_dir / "resources.json").is_file()

    read_text = Path.read_text

    def low_memory(path, *args, **kwargs):
        if path == Path("/proc/meminfo"):
            return "MemAvailable: 1 kB\n"
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", low_memory)
    monkeypatch.setattr(tool, "capture", lambda root: {"dirty": False})
    monkeypatch.setattr(tool, "load_contract", lambda path: SimpleNamespace(require_ready=lambda root: None))
    output = tmp_path / "must-not-start"
    with pytest.raises(ValueError, match="insufficient screening memory"):
        tool.screen(output)
    assert not output.exists()
