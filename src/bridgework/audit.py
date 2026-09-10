"""
Audit trail — Blueprint §E, §J.

A finance professional must be able to trace input -> calculation ->
attribution -> conclusion end-to-end. run_manifest() produces the
reproducibility record attached to every report: a hash of the exact
inputs used, the code version, and a timestamp. No network calls, no
environment reads beyond git/system clock (never in the calculation path
itself -- audit.py is metadata, not part of compute_fcf's dependency
chain).
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone

from .model import Drivers


def _input_hash(v1: Drivers, v2: Drivers, changed: tuple) -> str:
    payload = json.dumps(
        {"v1": asdict(v1), "v2": asdict(v2), "changed": list(changed)}, sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _code_version() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown (not a git checkout)"


def _dependency_fingerprint() -> str:
    """Hash of the installed versions of the packages the calculation
    depends on. The reproducibility claim is only meaningful against a
    known dependency set; recording python and platform but not package
    versions left the claim resting on luck (adversarial review finding)."""
    import importlib.metadata as md

    parts = []
    for pkg in ("pandas", "numpy", "scipy", "SALib", "openpyxl", "matplotlib", "PyYAML"):
        try:
            parts.append(f"{pkg}=={md.version(pkg)}")
        except md.PackageNotFoundError:
            parts.append(f"{pkg}==absent")
    joined = ";".join(parts)
    return f"{hashlib.sha256(joined.encode()).hexdigest()[:12]} ({joined})"


def run_manifest(v1: Drivers, v2: Drivers, changed: tuple) -> dict[str, str]:
    return {
        "dependency_fingerprint": _dependency_fingerprint(),
        "input_hash": _input_hash(v1, v2, changed),
        "code_version": _code_version(),
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


__all__ = ["run_manifest"]
