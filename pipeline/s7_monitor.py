"""Stage 6b — monitoring and the feedback loop.

Computes the Population Stability Index between the training distribution and a
freshly served batch. PSI is the standard drift statistic in this setting: the
usual reading is that below 0.10 the population is stable, 0.10–0.25 warrants
attention, and above 0.25 the shift is material. The threshold is configurable.

When drift crosses the threshold, the monitor writes a TRIGGERS_RETRAIN edge
from the drift report back to the raw dataset node. That single edge is what
closes the thread into a loop: the next traversal from the raw data reaches the
drift report that sent the pipeline round again.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pandas as pd

from thread import ThreadLedger, code_rev, environment_digest

from .common import banner, ensure_dirs, load_config
from .s6_serve import score_batch


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index over quantile bins of the reference sample."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    quantiles = np.linspace(0, 100, bins + 1)
    edges = np.percentile(expected, quantiles)
    edges[0], edges[-1] = -np.inf, np.inf
    edges = np.unique(edges)
    if len(edges) < 3:
        return 0.0
    e_counts, _ = np.histogram(expected, bins=edges)
    a_counts, _ = np.histogram(actual, bins=edges)
    e_frac = np.clip(e_counts / max(e_counts.sum(), 1), 1e-6, None)
    a_frac = np.clip(a_counts / max(a_counts.sum(), 1), 1e-6, None)
    return float(np.sum((a_frac - e_frac) * np.log(a_frac / e_frac)))


def simulate_shift(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Age the machines: more tool wear and slightly higher torque.

    This stands in for the passage of time in a real deployment. It is applied
    only to the monitored batch, never to the training data, and the shift
    parameters are recorded on the drift report so the experiment is honest
    about being simulated.
    """
    sim = cfg["monitor"]["drift_simulation"]
    out = df.copy()
    if "tool_wear_min" in out.columns:
        out["tool_wear_min"] = out["tool_wear_min"] + sim["tool_wear_offset_min"]
    if "torque_Nm" in out.columns:
        out["torque_Nm"] = out["torque_Nm"] * sim["torque_scale"]
    # recompute the engineered features so the shift propagates correctly
    if {"tool_wear_min", "torque_Nm"} <= set(out.columns):
        out["wear_torque"] = out["tool_wear_min"] * out["torque_Nm"]
    if {"torque_Nm", "rot_speed_rpm"} <= set(out.columns):
        out["power_W"] = out["torque_Nm"] * out["rot_speed_rpm"] * (2 * np.pi / 60)
    return out


def run(cfg: dict[str, Any], led: ThreadLedger, feature_id: str,
        raw_id: str | None = None) -> dict[str, Any]:
    ensure_dirs(cfg)
    banner("stage 7 · monitoring & feedback")

    fnode = led.get_node(feature_id)
    if fnode is None:
        raise RuntimeError("feature_set node not found")
    path = fnode.attrs["path"]
    reference = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)

    shifted = simulate_shift(reference, cfg)
    served = score_batch(cfg, led, shifted, "production-week-01", feature_id)

    monitored = [c for c in ("air_temp_K", "process_temp_K", "rot_speed_rpm",
                             "torque_Nm", "tool_wear_min", "temp_diff_K",
                             "power_W", "wear_torque")
                 if c in reference.columns]

    with led.run("monitor", code_rev=code_rev("."),
                 environment=environment_digest(),
                 psi_threshold=cfg["monitor"]["psi_threshold"]) as run_h:

        per_feature = {c: round(psi(reference[c].values, shifted[c].values), 4)
                       for c in monitored}
        worst_feature = max(per_feature, key=per_feature.get)
        worst = per_feature[worst_feature]
        threshold = cfg["monitor"]["psi_threshold"]
        drifted = worst >= threshold

        report_path = os.path.join(cfg["paths"]["reports"], "drift_report.json")
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump({"psi": per_feature, "threshold": threshold,
                       "drifted": drifted,
                       "simulation": cfg["monitor"]["drift_simulation"]},
                      fh, indent=2)

        node = run_h.node("drift_report", "production-week-01",
                          version=f"psi-{worst:.3f}",
                          digest=f"drift-{served['batch']}",
                          psi=worst, worst_feature=worst_feature,
                          per_feature=per_feature, threshold=threshold,
                          drifted=drifted, simulated=True,
                          simulation=cfg["monitor"]["drift_simulation"],
                          path=report_path)
        run_h.edge(node, served["batch"], "OBSERVED_ON")
        run_h.produced(node)

        for c, v in sorted(per_feature.items(), key=lambda kv: -kv[1]):
            flag = "  <-- drift" if v >= threshold else ""
            print(f"   PSI {c:<18} {v:.4f}{flag}")

        if drifted and raw_id:
            run_h.edge(node, raw_id, "TRIGGERS_RETRAIN",
                       reason=f"PSI {worst:.3f} on {worst_feature} "
                              f">= {threshold}")
            print(f"   feedback      drift {worst:.3f} >= {threshold} "
                  f"— retrain edge written back to the raw dataset")
        elif drifted:
            print(f"   feedback      drift detected but no raw node supplied")
        else:
            print(f"   feedback      no drift above {threshold}")

        return {"drift": node, "psi": worst, "drifted": drifted,
                "per_feature": per_feature}


if __name__ == "__main__":
    cfg = load_config()
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        fs = led.latest("feature_set")
        raw = led.latest("dataset", f"{cfg['dataset']['name']}-raw")
        if fs is None:
            raise SystemExit("run stages 1-5 first")
        run(cfg, led, fs.id, raw.id if raw else None)
