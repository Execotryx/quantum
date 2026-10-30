"""Explicit acquisition and immutable asset inventory. No credential handling."""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .errors import ValidationError
from .io import sha256, write_json
from .official import METRIC_V10_SHA256, tree_manifest

METRIC_URL = "https://www.kaggle.com/api/v1/kernels/pull/metric/google-quantum-ai-metric"


def acquire_metric(destination, expected_hash, expected_version=10):
    destination = Path(destination)
    if destination.exists():
        raise ValidationError("metric destination already exists; preserve pinned bytes")
    response = json.loads(urllib.request.urlopen(METRIC_URL, timeout=30).read())
    version = response["metadata"]["currentVersionNumber"]
    if version != expected_version:
        raise ValidationError(f"metric version changed to {version}; reconcile before adoption")
    source = response["blob"]["sourceNullable"].encode()
    import hashlib

    if hashlib.sha256(source).hexdigest() != expected_hash:
        raise ValidationError("metric bytes changed; reconcile before adoption")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source)
    return {
        "origin": METRIC_URL,
        "version": version,
        "path": str(destination),
        "sha256": sha256(destination),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "redistribution": "not redistributed; retrieve from official source",
    }


def pin_backend(metric, verifiers, kickmix, output):
    if sha256(Path(metric)) != METRIC_V10_SHA256:
        raise ValidationError("pin only the reviewed official metric v10 bytes")
    config = {
        "metric_notebook": str(Path(metric).resolve()),
        "metric_sha256": sha256(Path(metric)),
        "metric_version": 10,
        "verifiers_root": str(Path(verifiers).resolve()),
        "verifiers_files": tree_manifest(verifiers),
        "kickmix_root": str(Path(kickmix).resolve()),
        "kickmix_files": tree_manifest(kickmix),
    }
    write_json(Path(output), config)
    return config
