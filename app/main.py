"""HTTP surface: the API the dashboard talks to, and the dashboard itself.

    uvicorn app.main:app --port 8000        (or: python run.py serve)

The backend is a thin layer over the ledger and the promoted model. It holds no
state of its own — every number the frontend displays is read from the ledger at
request time, which is the point: the thread is the source of truth, and the
dashboard is just a view onto it.

Every prediction response carries the deployment version, the model digest and
the deployment's node id, so the frontend can take a prediction it has just
received and ask `/api/trace/{node_id}` what produced it. That round trip —
prediction to full provenance in two calls — is the project's claim made
operable.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pipeline.common import dataset_source, load_config
from pipeline.s3_features import build_features
from pipeline.s6_serve import load_deployment
from thread import ThreadLedger

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")

CFG = load_config()

app = FastAPI(
    title="Digital Thread Analytics",
    description="Prediction service and lineage explorer over the thread ledger.",
    version="0.1.0",
)


@contextmanager
def ledger() -> Iterator[ThreadLedger]:
    """A short-lived connection per request.

    SQLite connections are not safe to share across threads, and the ledger is
    append-only, so opening one per request costs almost nothing and avoids the
    whole class of problems that a shared handle would invite.
    """
    led = ThreadLedger(CFG["paths"]["ledger"])
    try:
        yield led
    finally:
        led.close()


def _node_brief(n) -> dict[str, Any]:
    return {
        "id": n.id,
        "type": n.type,
        "name": n.name,
        "version": n.version,
        "label": n.label,
        "created_at": n.created_at,
        "attrs": n.attrs,
    }


def _require_pipeline_has_run() -> None:
    if not os.path.exists(CFG["paths"]["ledger"]):
        raise HTTPException(
            503,
            "No ledger found. Run the pipeline first: python run.py pipeline",
        )


# --------------------------------------------------------------------- health
@app.get("/api/health", tags=["status"])
def health() -> dict[str, Any]:
    """Whether anything is deployed, and what."""
    if not os.path.exists(CFG["paths"]["ledger"]):
        return {"status": "no-ledger",
                "detail": "run the pipeline first: python run.py pipeline"}
    with ledger() as led:
        dep = led.latest("deployment")
        if dep is None:
            return {"status": "no-deployment",
                    "detail": "the pipeline has run but nothing was promoted"}
        return {
            "status": "ok",
            "deployment": dep.version,
            "model": dep.attrs.get("model"),
            "model_digest": dep.attrs.get("model_digest"),
            "deployment_node": dep.id,
        }


# ------------------------------------------------------------------- overview
@app.get("/api/overview", tags=["status"])
def overview() -> dict[str, Any]:
    """Everything the dashboard's header needs, in one call."""
    _require_pipeline_has_run()
    with ledger() as led:
        stats = led.stats()
        dep = led.latest("deployment")
        raw = led.latest("dataset", f"{CFG['dataset']['name']}-raw")
        clean = led.latest("dataset", f"{CFG['dataset']['name']}-clean")
        feats = led.latest("feature_set")
        drift = led.latest("drift_report")

        return {
            "project": CFG["project"],
            "ledger": stats,
            "deployment": _node_brief(dep) if dep else None,
            "dataset": {
                "raw": _node_brief(raw) if raw else None,
                "clean": _node_brief(clean) if clean else None,
                "origin": raw.attrs.get("origin") if raw else dataset_source(CFG),
                "positive_rate": clean.attrs.get("positive_rate") if clean else None,
            },
            "feature_set": _node_brief(feats) if feats else None,
            "drift": {
                "psi": drift.attrs.get("psi") if drift else None,
                "threshold": drift.attrs.get("threshold") if drift else None,
                "drifted": drift.attrs.get("drifted") if drift else None,
                "worst_feature": drift.attrs.get("worst_feature") if drift else None,
            } if drift else None,
        }


# --------------------------------------------------------------------- models
@app.get("/api/models", tags=["lifecycle"])
def models() -> dict[str, Any]:
    """Every candidate that was trained, and which one was promoted."""
    _require_pipeline_has_run()
    with ledger() as led:
        dep = led.latest("deployment")
        promoted = dep.attrs.get("model_digest") if dep else None
        metric = CFG["train"]["primary_metric"]
        rows = []
        for n in led.find(node_type="model"):
            rows.append({
                "id": n.id,
                "name": n.name,
                "algorithm": n.attrs.get("algorithm"),
                "params": n.attrs.get("params"),
                "seed": n.attrs.get("seed"),
                "metrics": {k: n.attrs.get(k) for k in
                            ("average_precision", "roc_auc", "f1",
                             "precision", "recall")},
                "mlflow_run_id": n.attrs.get("mlflow_run_id"),
                "promoted": n.digest == promoted,
            })
        rows.sort(key=lambda r: r["metrics"].get(metric) or 0, reverse=True)
        return {"primary_metric": metric,
                "gate": CFG["evaluate"]["promote_if_better_than"],
                "models": rows}


# ---------------------------------------------------------------- validation
@app.get("/api/validation", tags=["lifecycle"])
def validation() -> dict[str, Any]:
    """The data quality checks and their verdicts."""
    _require_pipeline_has_run()
    with ledger() as led:
        val = led.latest("validation")
        if val is None:
            raise HTTPException(404, "no validation report in the ledger")
        return {
            "id": val.id,
            "passed": val.attrs.get("passed"),
            "checks": val.attrs.get("checks"),
            "failed": val.attrs.get("failed"),
            "detail": val.attrs.get("detail", []),
        }


# --------------------------------------------------------------------- drift
@app.get("/api/drift", tags=["lifecycle"])
def drift() -> dict[str, Any]:
    """The latest drift report, per feature."""
    _require_pipeline_has_run()
    with ledger() as led:
        d = led.latest("drift_report")
        if d is None:
            raise HTTPException(404, "no drift report in the ledger")
        per = d.attrs.get("per_feature", {})
        return {
            "id": d.id,
            "psi": d.attrs.get("psi"),
            "threshold": d.attrs.get("threshold"),
            "drifted": d.attrs.get("drifted"),
            "worst_feature": d.attrs.get("worst_feature"),
            "simulated": d.attrs.get("simulated"),
            "simulation": d.attrs.get("simulation"),
            "per_feature": sorted(
                ({"feature": k, "psi": v} for k, v in per.items()),
                key=lambda r: -r["psi"]),
        }


# --------------------------------------------------------------------- nodes
@app.get("/api/nodes", tags=["lineage"])
def nodes(type: str | None = Query(None, description="filter by node type"),
          ) -> dict[str, Any]:
    """Browse the ledger's contents."""
    _require_pipeline_has_run()
    with ledger() as led:
        found = led.find(node_type=type)
        return {"count": len(found),
                "nodes": [_node_brief(n) for n in found]}


@app.get("/api/trace/{node_id}", tags=["lineage"])
def trace(node_id: str) -> dict[str, Any]:
    """Provenance: everything this artifact depended on, and how long it took."""
    _require_pipeline_has_run()
    with ledger() as led:
        started = time.perf_counter()
        try:
            bundle = led.trace(node_id)
        except Exception as exc:                             # noqa: BLE001
            raise HTTPException(404, str(exc)) from exc
        elapsed_ms = (time.perf_counter() - started) * 1000

        rows = [{"id": n.id, "type": n.type, "label": n.label,
                 "via": rel, "depth": depth, "attrs": n.attrs}
                for n, rel, depth in led.upstream(node_id)]
        rows.sort(key=lambda r: r["depth"])
        return {"node": bundle["node"],
                "nodes_reached": bundle["nodes_reached"],
                "elapsed_ms": round(elapsed_ms, 3),
                "provenance": rows}


@app.get("/api/impact/{node_id}", tags=["lineage"])
def impact(node_id: str) -> dict[str, Any]:
    """The other direction: everything downstream of this artifact."""
    _require_pipeline_has_run()
    with ledger() as led:
        if led.get_node(node_id) is None:
            raise HTTPException(404, f"node {node_id} not in the ledger")
        started = time.perf_counter()
        rows = led.downstream(node_id)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {"count": len(rows),
                "elapsed_ms": round(elapsed_ms, 3),
                "affected": [{"id": n.id, "type": n.type, "label": n.label,
                              "via": rel, "depth": depth}
                             for n, rel, depth in sorted(rows, key=lambda r: r[2])]}


@app.get("/api/graph", tags=["lineage"])
def graph() -> dict[str, Any]:
    """The whole ledger as nodes and edges, for the graph view."""
    _require_pipeline_has_run()
    with ledger() as led:
        return led.to_dict()


# ------------------------------------------------------------------- predict
class Reading(BaseModel):
    """One machine reading, in the units the raw dataset uses."""
    air_temp_K: float = Field(298.1, ge=250, le=400, examples=[298.1])
    process_temp_K: float = Field(308.6, ge=250, le=400, examples=[308.6])
    rot_speed_rpm: float = Field(1551, gt=0, le=10000, examples=[1551])
    torque_Nm: float = Field(42.8, ge=0, le=200, examples=[42.8])
    tool_wear_min: float = Field(108, ge=0, le=1000, examples=[108])
    type: str = Field("M", pattern="^[LMH]$", examples=["L", "M", "H"])


@app.post("/api/predict", tags=["serving"])
def predict(reading: Reading) -> dict[str, Any]:
    """Score one reading and return the thread alongside the answer."""
    _require_pipeline_has_run()
    with ledger() as led:
        try:
            dep, bundle = load_deployment(CFG, led)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

        started = time.perf_counter()
        row = pd.DataFrame([reading.model_dump()])
        feats = build_features(row, CFG)
        # a single reading only produces the one-hot column for its own quality
        # variant, so the rest are filled in to match the training matrix
        for col in bundle["features"]:
            if col not in feats.columns:
                feats[col] = 0
        prob = float(bundle["estimator"].predict_proba(
            feats[bundle["features"]])[:, 1][0])
        elapsed_ms = (time.perf_counter() - started) * 1000

        derived = {k: round(float(feats[k].iloc[0]), 3)
                   for k in ("temp_diff_K", "power_W", "wear_torque")
                   if k in feats.columns}

        return {
            "failure_probability": round(prob, 6),
            "prediction": int(prob >= 0.5),
            "elapsed_ms": round(elapsed_ms, 3),
            "derived_features": derived,
            # the thread travels with the answer
            "lineage": {
                "deployment": dep.version,
                "model": dep.attrs.get("model"),
                "model_digest": dep.attrs.get("model_digest"),
                "deployment_node": dep.id,
                "trace_url": f"/api/trace/{dep.id}",
            },
        }


# -------------------------------------------------------------------- static
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
