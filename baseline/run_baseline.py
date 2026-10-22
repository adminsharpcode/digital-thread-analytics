"""The control condition: the same pipeline with no thread.

This is deliberately written the way a data science project usually looks — one
script, results printed and a model dumped to disk, no record of which data or
code produced it. It exists so the evaluation has something to measure against:
identical model, identical metrics, no lineage.

    python -m baseline.run_baseline
"""

from __future__ import annotations

import math
import os
import sys
import time

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.common import fetch_dataset, load_config          # noqa: E402

try:
    import joblib
except ImportError:                                             # pragma: no cover
    joblib = None


def main() -> dict[str, float]:
    cfg = load_config()
    started = time.perf_counter()

    csv = fetch_dataset(cfg)
    df = pd.read_csv(csv)

    df = df.drop(columns=[c for c in ["UDI", "Product ID", "TWF", "HDF",
                                      "PWF", "OSF", "RNF"] if c in df.columns])
    df = df.rename(columns={
        "Air temperature [K]": "air_temp_K",
        "Process temperature [K]": "process_temp_K",
        "Rotational speed [rpm]": "rot_speed_rpm",
        "Torque [Nm]": "torque_Nm",
        "Tool wear [min]": "tool_wear_min",
        "Machine failure": "machine_failure",
        "Type": "type",
    }).drop_duplicates().reset_index(drop=True)

    df["temp_diff_K"] = df["process_temp_K"] - df["air_temp_K"]
    df["power_W"] = df["torque_Nm"] * df["rot_speed_rpm"] * (2 * math.pi / 60)
    df["wear_torque"] = df["tool_wear_min"] * df["torque_Nm"]
    df = pd.concat([df.drop(columns=["type"]),
                    pd.get_dummies(df["type"], prefix="type", dtype=int)], axis=1)

    y = df["machine_failure"]
    X = df.drop(columns=["machine_failure"])
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=cfg["train"]["test_size"],
        random_state=cfg["seed"], stratify=y)

    scores: dict[str, float] = {}
    best, best_score = None, -1.0
    for name, est in {
        "logistic_regression": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=1000,
                                       random_state=cfg["seed"]))]),
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=2,
            class_weight="balanced_subsample", random_state=cfg["seed"], n_jobs=-1),
    }.items():
        est.fit(X_tr, y_tr)
        prob = est.predict_proba(X_te)[:, 1]
        ap = float(average_precision_score(y_te, prob))
        scores[name] = round(ap, 4)
        print(f"{name:<20} PR-AUC {ap:.4f}  ROC-AUC {roc_auc_score(y_te, prob):.4f}  "
              f"F1 {f1_score(y_te, (prob >= 0.5).astype(int), zero_division=0):.4f}")
        if ap > best_score:
            best, best_score = est, ap

    os.makedirs("artifacts/baseline", exist_ok=True)
    if joblib is not None:
        joblib.dump(best, "artifacts/baseline/model.joblib")

    elapsed = time.perf_counter() - started
    print(f"\nwall clock {elapsed:.2f} s — model written to "
          f"artifacts/baseline/model.joblib")
    print("no record of which data version, code revision or parameters "
          "produced it")
    return {"elapsed": elapsed, **scores}


if __name__ == "__main__":
    main()
