import importlib.metadata
import os
import platform
import subprocess
import sys
from pathlib import Path

from .io import sha256


def capture(root: Path):
    def git(*args):
        completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return completed.stdout.strip() if completed.returncode == 0 else None

    import numpy as np

    revision = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    return {
        "source_revision": revision,
        "dirty": status is None or bool(status),
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "thread_settings": {
            k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
        "numpy_backend": np.show_config(mode="dicts"),
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "pandas")},
        "dependency_lock_sha256": sha256(root / "uv.lock") if (root / "uv.lock").is_file() else None,
    }
