"""Stage 2 — cleaning and exploratory profiling.

Drops identifier and leakage columns, normalises column names, and writes a
compact profile. The cleaned dataset is a new node DERIVED_FROM the raw one:
the ledger never overwrites, so both versions stay addressable forever.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd

from thread import ThreadLedger, code_rev, environment_digest, frame_digest

from .common import banner, ensure_dirs, load_config

CLEAN_NAMES = {
    "Air temperature [K]": "air_temp_K",
    "Process temperature [K]": "process_temp_K",
    "Rotational speed [rpm]": "rot_speed_rpm",
    "Torque [Nm]": "torque_Nm",
    "Tool wear [min]": "tool_wear_min",
    "Machine failure": "machine_failure",
    "Type": "type",
}


def profile(df: pd.DataFrame) -> dict[str, Any]:
    """A lightweight stand-in for ydata-profiling, kept dependency-free."""
    num = df.select_dtypes("number")
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "numeric_summary": {
            c: {k: round(float(v), 4) for k, v in num[c].describe().items()}
            for c in num.columns
        },
        "categorical_levels": {
            c: df[c].value_counts().to_dict()
            for c in df.select_dtypes("object").columns
            if df[c].nunique() <= 20
        },
    }


def clean(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    drop = [c for c in cfg["dataset"]["id_columns"] + cfg["dataset"]["leakage_columns"]
            if c in df.columns]
    out = df.drop(columns=drop)
    out = out.rename(columns={k: v for k, v in CLEAN_NAMES.items() if k in out.columns})
    out = out.drop_duplicates().reset_index(drop=True)
    return out


def run(cfg: dict[str, Any], led: ThreadLedger, raw_id: str) -> dict[str, str]:
    ensure_dirs(cfg)
    banner("stage 2 · cleaning & profiling")

    raw_node = led.get_node(raw_id)
    if raw_node is None:
        raise RuntimeError("raw dataset node not found — run stage 1 first")

    with led.run("clean", code_rev=code_rev("."),
                 environment=environment_digest()) as run_h:
        df = pd.read_csv(raw_node.attrs["path"])
        dropped = [c for c in cfg["dataset"]["id_columns"] + cfg["dataset"]["leakage_columns"]
                   if c in df.columns]
        cleaned = clean(df, cfg)

        out_path = os.path.join(cfg["paths"]["processed"], "clean.parquet")
        try:
            cleaned.to_parquet(out_path, index=False)
        except Exception:                                    # noqa: BLE001
            out_path = os.path.join(cfg["paths"]["processed"], "clean.csv")
            cleaned.to_csv(out_path, index=False)

        digest = frame_digest(cleaned)
        prof = profile(cleaned)
        prof_path = os.path.join(cfg["paths"]["reports"], "profile_clean.json")
        with open(prof_path, "w", encoding="utf-8") as fh:
            json.dump(prof, fh, indent=2, default=str)

        node = run_h.node("dataset", f"{cfg['dataset']['name']}-clean",
                          version=digest[:12], digest=digest,
                          path=out_path, rows=len(cleaned),
                          columns=len(cleaned.columns),
                          dropped_columns=dropped,
                          profile_path=prof_path,
                          positive_rate=round(
                              float(cleaned["machine_failure"].mean()), 5))
        run_h.edge(node, raw_id, "DERIVED_FROM",
                   transform="drop id+leakage columns, rename, dedupe")
        run_h.produced(node)

        print(f"   dropped       {dropped}")
        print(f"   clean dataset {len(cleaned)} rows x {len(cleaned.columns)} cols  "
              f"sha256:{digest[:12]}")
        print(f"   positives     {cleaned['machine_failure'].mean():.3%}")
        return {"clean": node}


if __name__ == "__main__":
    cfg = load_config()
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        raw = led.latest("dataset", f"{cfg['dataset']['name']}-raw")
        if raw is None:
            raise SystemExit("run stage 1 first")
        run(cfg, led, raw.id)
