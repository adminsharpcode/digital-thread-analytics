"""Stage 6a — serving.

`score_batch(...)` scores a batch and records a `prediction_batch` node
SERVED_BY the deployment, which is what the orchestrated flow calls.
`load_deployment(...)` resolves whatever is currently promoted.

The HTTP surface lives in `app/main.py` and builds on these two functions, so
this module stays free of any web dependency and the pipeline runs without one.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd

from thread import ThreadLedger, code_rev, environment_digest, frame_digest

from .common import banner, ensure_dirs, load_config

try:
    import joblib
except ImportError:                                          # pragma: no cover
    joblib = None                                            # type: ignore


def load_deployment(cfg: dict[str, Any], led: ThreadLedger):
    dep = led.latest("deployment")
    if dep is None:
        raise RuntimeError("nothing deployed — run stage 5 first")
    if joblib is None:
        raise RuntimeError("joblib is required to load the model")
    bundle = joblib.load(dep.attrs["model_path"])
    return dep, bundle


def score_batch(cfg: dict[str, Any], led: ThreadLedger, frame: pd.DataFrame,
                batch_name: str, upstream_feature_id: str | None = None,
                ) -> dict[str, Any]:
    """Score a feature frame and record the batch in the ledger."""
    ensure_dirs(cfg)
    dep, bundle = load_deployment(cfg, led)
    est, features = bundle["estimator"], bundle["features"]

    with led.run("serve", code_rev=code_rev("."),
                 environment=environment_digest(),
                 deployment=dep.version, batch=batch_name) as run_h:

        X = frame[features]
        prob = est.predict_proba(X)[:, 1]
        pred = (prob >= 0.5).astype(int)

        out = frame.copy()
        out["failure_probability"] = prob.round(6)
        out["prediction"] = pred
        out_path = os.path.join(cfg["paths"]["reports"], f"predictions_{batch_name}.csv")
        out.to_csv(out_path, index=False)

        digest = frame_digest(out[["failure_probability", "prediction"]])
        node = run_h.node("prediction_batch", batch_name,
                          version=dep.version, digest=digest,
                          rows=int(len(out)),
                          flagged=int(pred.sum()),
                          mean_probability=round(float(prob.mean()), 6),
                          deployment=dep.version,
                          model=dep.attrs.get("model"),
                          model_digest=dep.attrs.get("model_digest"),
                          path=out_path)
        run_h.edge(node, dep.id, "SERVED_BY")
        if upstream_feature_id:
            run_h.edge(node, upstream_feature_id, "DERIVED_FROM")
        run_h.produced(node)

        print(f"   scored        {len(out)} rows on deployment {dep.version} "
              f"({int(pred.sum())} flagged)")
        return {"batch": node, "path": out_path, "probabilities": prob,
                "deployment": dep.version}


def run(cfg: dict[str, Any], led: ThreadLedger,
        feature_id: str) -> dict[str, Any]:
    banner("stage 6 · serving")
    fnode = led.get_node(feature_id)
    if fnode is None:
        raise RuntimeError("feature_set node not found")
    path = fnode.attrs["path"]
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    return score_batch(cfg, led, df, "holdout-baseline", feature_id)


if __name__ == "__main__":
    cfg = load_config()
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        fs = led.latest("feature_set")
        if fs is None:
            raise SystemExit("run stage 3 first")
        run(cfg, led, fs.id)
