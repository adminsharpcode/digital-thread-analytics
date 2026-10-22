"""Environment and content fingerprinting.

Reproducibility needs three fingerprints, not one: what the data was, what the
code was, and what the environment was. These helpers produce all three as
stable digests that the ledger stores verbatim.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from typing import Any

# Content fingerprinting is part of the cost of carrying the thread, separate
# from the cost of writing to the ledger. The evaluation reports both, so the
# two are accumulated here rather than guessed at.
DIGEST_STATS: dict[str, float] = {"seconds": 0.0, "calls": 0.0}


def reset_digest_stats() -> None:
    DIGEST_STATS["seconds"] = 0.0
    DIGEST_STATS["calls"] = 0.0

try:                                   # pandas is required by the pipeline,
    import pandas as pd                # but the ledger itself must not need it
except ImportError:                    # pragma: no cover
    pd = None                          # type: ignore[assignment]


def file_digest(path: str | os.PathLike[str], chunk: int = 1 << 20) -> str:
    """SHA-256 of a file's bytes."""
    t0 = time.perf_counter()
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    DIGEST_STATS["seconds"] += time.perf_counter() - t0
    DIGEST_STATS["calls"] += 1
    return h.hexdigest()


def frame_digest(df: "pd.DataFrame") -> str:
    """Order-independent content digest of a dataframe.

    Hashing the values *and* the column names means a reordered or renamed
    column produces a different dataset version, which is what we want: the
    ledger should notice a silent schema change.
    """
    if pd is None:                                   # pragma: no cover
        raise RuntimeError("pandas is required for frame_digest")
    t0 = time.perf_counter()
    h = hashlib.sha256()
    h.update(",".join(map(str, df.columns)).encode())
    h.update(str(df.shape).encode())
    values = pd.util.hash_pandas_object(df, index=True).values
    h.update(values.tobytes())
    DIGEST_STATS["seconds"] += time.perf_counter() - t0
    DIGEST_STATS["calls"] += 1
    return h.hexdigest()


def code_rev(repo_root: str | os.PathLike[str] = ".") -> str:
    """Current git commit, or a digest of the source tree when git is absent."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root),
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            dirty = subprocess.run(["git", "status", "--porcelain"],
                                   cwd=str(repo_root), capture_output=True,
                                   text=True, timeout=10).stdout.strip()
            rev = out.stdout.strip()
            return f"{rev}-dirty" if dirty else rev
    except (OSError, subprocess.SubprocessError):
        pass
    # fallback: hash every tracked-looking source file
    h = hashlib.sha256()
    for root, dirs, files in sorted(os.walk(repo_root)):
        dirs[:] = [d for d in sorted(dirs)
                   if d not in {".git", "__pycache__", "data", "artifacts",
                                ".venv", "node_modules", ".dvc"}]
        for name in sorted(files):
            if name.endswith(".py") or name.endswith(".yaml"):
                h.update(name.encode())
                h.update(file_digest(os.path.join(root, name)).encode())
    return "sha256:" + h.hexdigest()[:16]


def environment_digest() -> str:
    """Digest of the interpreter plus the versions of the libraries that matter."""
    payload: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "machine": platform.machine(),
    }
    for mod in ("pandas", "numpy", "sklearn", "scipy"):
        try:
            payload[mod] = __import__(mod).__version__
        except Exception:                            # noqa: BLE001
            payload[mod] = "absent"
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def environment_report() -> dict[str, Any]:
    """Human-readable twin of environment_digest, stored as node attributes."""
    report: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
    }
    for mod in ("pandas", "numpy", "sklearn", "scipy"):
        try:
            report[mod] = __import__(mod).__version__
        except Exception:                            # noqa: BLE001
            report[mod] = "absent"
    return report
