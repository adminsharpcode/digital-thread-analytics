"""Stage 4 — model training with experiment tracking.

Each candidate is trained inside its own ledger run, so the thread records one
`run` node per candidate with its parameters, the feature set it trained on,
the code revision, the environment, and the model it produced.

MLflow is used when it is installed, and its run id is written onto the model
node as an attribute. The pipeline does not depend on it: the ledger is the
system of record, MLflow is one of the tools it points at.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from thread import ThreadLedger, code_rev, environment_digest

from .common import banner, ensure_dirs, load_config

try:
    import joblib
except ImportError:                                          # pragma: no cover
    joblib = None                                            # type: ignore

try:
    import mlflow
    _HAS_MLFLOW = True
except Exception:                                            # noqa: BLE001
    _HAS_MLFLOW = False


def build_estimator(name: str, params: dict[str, Any], seed: int):
    if name == "logistic_regression":
        return Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(random_state=seed, **params)),
        ])
    if name == "random_forest":
        return RandomForestClassifier(random_state=seed, n_jobs=-1, **params)
    raise ValueError(f"unknown model {name!r}")


def metrics_for(y_true, y_prob, threshold: float = 0.5) -> dict[str, float]:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "average_precision": round(float(average_precision_score(y_true, y_prob)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
    }


def run(cfg: dict[str, Any], led: ThreadLedger, feature_id: str) -> dict[str, Any]:
    ensure_dirs(cfg)
    banner("stage 4 · training & tracking")

    fnode = led.get_node(feature_id)
    if fnode is None:
        raise RuntimeError("feature_set node not found — run stage 3 first")

    path = fnode.attrs["path"]
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    target = fnode.attrs["target"]
    X = df[fnode.attrs["features"]]
    y = df[target]

    seed = cfg["seed"]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=cfg["train"]["test_size"], random_state=seed,
        stratify=y if cfg["train"]["stratify"] else None)

    if _HAS_MLFLOW:
        mlflow.set_tracking_uri(f"file:{os.path.abspath(cfg['paths']['artifacts'])}/mlruns")
        mlflow.set_experiment(cfg["project"])

    produced: dict[str, str] = {}
    scores: dict[str, dict[str, float]] = {}

    for name, params in cfg["train"]["models"].items():
        with led.run(f"train:{name}", code_rev=code_rev("."),
                     environment=environment_digest(),
                     algorithm=name, seed=seed,
                     test_size=cfg["train"]["test_size"], **params) as run_h:

            run_h.used(feature_id, "TRAINED_ON")

            est = build_estimator(name, dict(params), seed)
            est.fit(X_tr, y_tr)
            prob_te = est.predict_proba(X_te)[:, 1]
            m = metrics_for(y_te, prob_te)
            scores[name] = m

            model_path = os.path.join(cfg["paths"]["models"], f"{name}.joblib")
            if joblib is not None:
                joblib.dump({"estimator": est, "features": list(X.columns),
                             "target": target}, model_path)

            mlflow_run_id = None
            if _HAS_MLFLOW:
                with mlflow.start_run(run_name=name) as mrun:
                    mlflow.log_params({**params, "seed": seed,
                                       "feature_set": fnode.digest[:12]})
                    mlflow.log_metrics(m)
                    mlflow_run_id = mrun.info.run_id

            digest = f"{name}-{fnode.digest[:12]}-{seed}"
            model_node = run_h.node(
                "model", name, version=fnode.digest[:12], digest=digest,
                algorithm=name, params=dict(params), seed=seed,
                path=model_path, feature_set=fnode.digest[:12],
                mlflow_run_id=mlflow_run_id, **m)
            run_h.produced(model_node)

            eval_node = run_h.node(
                "evaluation", f"{name}-holdout", version=fnode.digest[:12],
                digest=f"eval-{digest}", n_test=int(len(y_te)),
                positives=int(y_te.sum()), **m)
            run_h.edge(eval_node, model_node, "EVALUATES")
            produced[name] = model_node

            print(f"   {name:<20} PR-AUC {m['average_precision']:.3f}  "
                  f"ROC-AUC {m['roc_auc']:.3f}  F1 {m['f1']:.3f}  "
                  f"recall {m['recall']:.3f}")

    report_path = os.path.join(cfg["paths"]["reports"], "training_metrics.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(scores, fh, indent=2)

    if _HAS_MLFLOW:
        print("   mlflow        logged to artifacts/mlruns")
    else:
        print("   mlflow        not installed — ledger still holds every metric")

    return {"models": produced, "scores": scores}


if __name__ == "__main__":
    cfg = load_config()
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        fs = led.latest("feature_set")
        if fs is None:
            raise SystemExit("run stage 3 first")
        run(cfg, led, fs.id)
