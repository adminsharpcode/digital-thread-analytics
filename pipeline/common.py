"""Shared helpers for the pipeline stages."""

from __future__ import annotations

import io
import os
import urllib.request
import zipfile
from typing import Any

import yaml

CONFIG_PATH = os.environ.get("DTA_CONFIG", "config/config.yaml")


def load_config(path: str | None = None) -> dict[str, Any]:
    with open(path or CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def ensure_dirs(cfg: dict[str, Any]) -> None:
    for key in ("raw", "processed", "artifacts", "models", "reports"):
        os.makedirs(cfg["paths"][key], exist_ok=True)


def dataset_source(cfg: dict[str, Any]) -> str:
    """Where the raw CSV on disk actually came from ('uci' or 'synthetic')."""
    marker = os.path.join(cfg["paths"]["raw"], ".source")
    if os.path.exists(marker):
        with open(marker, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    return "unknown"


def _write_marker(cfg: dict[str, Any], value: str) -> None:
    with open(os.path.join(cfg["paths"]["raw"], ".source"), "w",
              encoding="utf-8") as fh:
        fh.write(value)


def fetch_dataset(cfg: dict[str, Any]) -> str:
    """Return a local path to the raw CSV, downloading it once if needed.

    The download is the only network call in the project and is skipped once
    the file is on disk, so the pipeline runs offline after the first pass.

    If the download fails and `dataset.allow_synthetic_fallback` is set, a
    replica is generated from the documented generation procedure instead. The
    replica is *not* the UCI file: it is clearly marked as such on disk and the
    ingestion stage records the distinction on the dataset node, which is
    precisely the sort of thing the thread exists to keep honest.
    """
    raw_dir = cfg["paths"]["raw"]
    os.makedirs(raw_dir, exist_ok=True)
    csv_path = os.path.join(raw_dir, cfg["dataset"]["csv_name"])
    if os.path.exists(csv_path):
        return csv_path

    url = cfg["dataset"]["url"]
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:   # noqa: S310
            payload = resp.read()
        if url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:
                    raise RuntimeError(f"no CSV inside {url}")
                with zf.open(names[0]) as src, open(csv_path, "wb") as dst:
                    dst.write(src.read())
        else:
            with open(csv_path, "wb") as dst:
                dst.write(payload)
        _write_marker(cfg, "uci")
        return csv_path
    except Exception as exc:                                    # noqa: BLE001
        if not cfg["dataset"].get("allow_synthetic_fallback"):
            raise RuntimeError(
                f"could not download the dataset from {url} ({exc}). "
                f"Either download it manually to {csv_path} or set "
                f"dataset.allow_synthetic_fallback: true in the config."
            ) from exc
        print(f"   ! download failed ({type(exc).__name__}) — generating a "
              f"specification replica instead")
        generate_ai4i(csv_path, n=cfg["validation"]["expected_rows"],
                      seed=cfg["seed"])
        _write_marker(cfg, "synthetic")
        return csv_path


def generate_ai4i(path: str, n: int = 10_000, seed: int = 42) -> str:
    """Build a replica of AI4I 2020 from its published description.

    The UCI dataset is itself synthetic. This function reproduces two things
    about it that the case study depends on — the marginal distributions of the
    process variables, and the prevalence and mechanism of failure — so that
    the pipeline can be exercised and timed without network access.

    Process variables follow the documented summary statistics: product quality
    L/M/H at 50/30/20 %, air temperature around 300 K with standard deviation
    2 K, process temperature roughly 10 K above it, rotational speed around
    1538 rpm bounded to [1168, 2886], torque around 40 Nm bounded to
    [3.8, 76.6], and tool wear spread over 0-253 minutes.

    Failures are then attributed to the five documented mechanisms, each firing
    on the rows most extreme by its own criterion:

        TWF  tool wear failure, wear between 200 and 240 minutes
        HDF  heat dissipation, temperature difference below 8.6 K with
             rotational speed below 1380 rpm
        PWF  power outside the 3500-9000 W band
        OSF  overstrain, wear x torque above 11000 / 12000 / 13000 Nm-min
             for L / M / H
        RNF  random failure, independent of the process values

    The mechanisms are assigned to disjoint sets of rows sized in the published
    proportions and scaled so the overall failure rate matches the documented
    3.39 %. A replica is not the dataset: published results must use the real
    file, and the ingestion stage records on the dataset node which of the two
    a given run actually used.
    """
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)

    quality = rng.choice(["L", "M", "H"], size=n, p=[0.5, 0.3, 0.2])

    air = np.clip(rng.normal(300.0, 2.0, n), 295.3, 304.5)
    process = np.clip(air + rng.normal(10.0, 1.0, n), 305.7, 313.8)
    speed = np.clip(rng.normal(1538.8, 179.3, n), 1168, 2886).round()
    torque = np.clip(rng.normal(39.99, 9.97, n), 3.8, 76.6)
    wear = np.clip(rng.uniform(0, 253, n), 0, 253).round()

    power = torque * speed * 2 * np.pi / 60
    temp_diff = process - air
    osf_limit = np.select([quality == "H", quality == "M"],
                          [13000, 12000], default=11000)

    # documented per-mode counts (120/115/95/98/5) rescaled so the union is the
    # documented 339 failing rows out of 10 000
    raw_counts = {"TWF": 120, "HDF": 115, "PWF": 95, "OSF": 98, "RNF": 5}
    scale = (0.0339 * n) / sum(raw_counts.values())
    counts = {k: max(1, int(round(v * scale * (n / 10_000)))) for k, v in raw_counts.items()}

    # each mechanism ranks the rows it would plausibly affect; the worst
    # offenders fail, and rows already failing are not reused
    severity = {
        "TWF": np.where((wear >= 200) & (wear <= 240), rng.random(n), -1.0),
        "HDF": -(temp_diff + speed / 1000.0),
        "PWF": np.maximum(3500.0 - power, power - 9000.0),
        "OSF": (wear * torque) - osf_limit,
        "RNF": rng.random(n),
    }

    modes = {k: np.zeros(n, dtype=int) for k in raw_counts}
    taken = np.zeros(n, dtype=bool)
    for mode in ("TWF", "HDF", "PWF", "OSF", "RNF"):
        order = np.argsort(-severity[mode])
        chosen: list[int] = []
        for idx in order:
            if len(chosen) >= counts[mode]:
                break
            if taken[idx]:
                continue
            if mode == "TWF" and severity["TWF"][idx] < 0:
                break                      # no eligible wear window left
            chosen.append(int(idx))
        modes[mode][chosen] = 1
        taken[chosen] = True

    failure = np.clip(sum(modes.values()), 0, 1)

    df = pd.DataFrame({
        "UDI": np.arange(1, n + 1),
        "Product ID": [f"{q}{i}" for q, i in
                       zip(quality, rng.integers(10000, 99999, n))],
        "Type": quality,
        "Air temperature [K]": air.round(1),
        "Process temperature [K]": process.round(1),
        "Rotational speed [rpm]": speed.astype(int),
        "Torque [Nm]": torque.round(1),
        "Tool wear [min]": wear.astype(int),
        "Machine failure": failure,
        "TWF": modes["TWF"], "HDF": modes["HDF"], "PWF": modes["PWF"],
        "OSF": modes["OSF"], "RNF": modes["RNF"],
    })
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    df.to_csv(path, index=False)
    return path


def banner(stage: str, message: str = "") -> None:
    line = f"-- {stage} " + "-" * max(0, 58 - len(stage))
    print(f"\n{line}")
    if message:
        print(f"   {message}")
