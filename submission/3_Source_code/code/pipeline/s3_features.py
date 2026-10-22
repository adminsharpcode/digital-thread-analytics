"""Stage 3 — feature engineering.

The three engineered features come straight from the failure mechanisms
documented with the AI4I 2020 data: heat-dissipation failure depends on the
temperature difference, power failure on torque times angular velocity, and
overstrain failure on tool wear times torque. Encoding that domain knowledge is
what makes the feature set worth versioning.

The feature_set node records the *definition* of each feature, not just the
resulting file, so the ledger can answer "how was power_W computed in the run
that produced the deployed model?" without reading any code.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any

import pandas as pd

from thread import ThreadLedger, code_rev, environment_digest, frame_digest

from .common import banner, ensure_dirs, load_config

DEFINITIONS = {
    "temp_diff_K": "process_temp_K - air_temp_K",
    "power_W": "torque_Nm * rot_speed_rpm * 2*pi/60",
    "wear_torque": "tool_wear_min * torque_Nm",
}


def build_features(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    out["temp_diff_K"] = out["process_temp_K"] - out["air_temp_K"]
    out["power_W"] = out["torque_Nm"] * out["rot_speed_rpm"] * (2 * math.pi / 60)
    out["wear_torque"] = out["tool_wear_min"] * out["torque_Nm"]
    for col in cfg["features"]["categorical"]:
        if col in out.columns:
            dummies = pd.get_dummies(out[col], prefix=col, dtype=int)
            out = pd.concat([out.drop(columns=[col]), dummies], axis=1)
    return out


def run(cfg: dict[str, Any], led: ThreadLedger, clean_id: str) -> dict[str, str]:
    ensure_dirs(cfg)
    banner("stage 3 · feature engineering")

    clean_node = led.get_node(clean_id)
    if clean_node is None:
        raise RuntimeError("clean dataset node not found — run stage 2 first")

    with led.run("features", code_rev=code_rev("."),
                 environment=environment_digest()) as run_h:
        path = clean_node.attrs["path"]
        df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
        feats = build_features(df, cfg)

        out_path = os.path.join(cfg["paths"]["processed"], "features.parquet")
        try:
            feats.to_parquet(out_path, index=False)
        except Exception:                                    # noqa: BLE001
            out_path = os.path.join(cfg["paths"]["processed"], "features.csv")
            feats.to_csv(out_path, index=False)

        digest = frame_digest(feats)
        target = "machine_failure"
        feature_names = [c for c in feats.columns if c != target]

        spec_path = os.path.join(cfg["paths"]["reports"], "feature_spec.json")
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump({"definitions": DEFINITIONS, "features": feature_names,
                       "target": target, "source_digest": clean_node.digest},
                      fh, indent=2)

        node = run_h.node("feature_set", f"{cfg['dataset']['name']}-features",
                          version=digest[:12], digest=digest,
                          path=out_path, rows=len(feats),
                          n_features=len(feature_names),
                          features=feature_names,
                          definitions=DEFINITIONS,
                          target=target, spec_path=spec_path)
        run_h.edge(node, clean_id, "DERIVED_FROM",
                   transform="domain features + one-hot encoding")
        run_h.produced(node)

        print(f"   engineered    {list(DEFINITIONS)}")
        print(f"   feature set   {len(feature_names)} features  sha256:{digest[:12]}")
        return {"features": node}


if __name__ == "__main__":
    cfg = load_config()
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        clean = led.latest("dataset", f"{cfg['dataset']['name']}-clean")
        if clean is None:
            raise SystemExit("run stage 2 first")
        run(cfg, led, clean.id)
