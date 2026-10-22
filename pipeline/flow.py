"""End-to-end orchestration.

    python -m pipeline.flow

Runs every stage in order against one ledger. Prefect or Airflow would wrap
these same functions as tasks in a DAG; the functions are written to be
orchestrator-agnostic so that swapping the scheduler does not touch the
lineage code. A Prefect flow is included below and activates only if Prefect
is installed.
"""

from __future__ import annotations

import time
from typing import Any

from thread import DIGEST_STATS, ThreadLedger, reset_digest_stats

from . import s1_ingest, s2_clean, s3_features, s4_train, s5_evaluate, s6_serve, s7_monitor
from .common import banner, ensure_dirs, load_config


def run_pipeline(cfg: dict[str, Any] | None = None,
                 ledger_path: str | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    ensure_dirs(cfg)
    reset_digest_stats()
    started = time.perf_counter()

    with ThreadLedger(ledger_path or cfg["paths"]["ledger"]) as led:
        s1 = s1_ingest.run(cfg, led)
        s2 = s2_clean.run(cfg, led, s1["raw"])
        s3 = s3_features.run(cfg, led, s2["clean"])
        s4 = s4_train.run(cfg, led, s3["features"])
        s5 = s5_evaluate.run(cfg, led, s4["models"])
        s6 = s6_serve.run(cfg, led, s3["features"])
        s7 = s7_monitor.run(cfg, led, s3["features"], s1["raw"])

        elapsed = time.perf_counter() - started
        stats = led.stats()

        banner("thread summary")
        print(f"   wall clock    {elapsed:.2f} s")
        print(f"   ledger        {stats['n_nodes']} nodes, {stats['n_edges']} edges, "
              f"{led.write_count} writes in {led.write_seconds:.3f} s "
              f"({led.write_seconds / elapsed:.1%} of wall clock)")
        print(f"   winner        {s5['winner']} "
              f"({cfg['train']['primary_metric']}={s5['score']:.4f})")
        print(f"   drift         PSI {s7['psi']:.3f} "
              f"({'above' if s7['drifted'] else 'below'} threshold)")

        from thread.viz import write_html
        page = write_html(led, f"{cfg['paths']['artifacts']}/thread.html")
        print(f"   visualisation {page}")
        print("\n   try:  python -m thread.query explain-model")
        print("         python -m thread.query stats\n")

        return {"stages": {"ingest": s1, "clean": s2, "features": s3,
                           "train": s4, "promote": s5, "serve": s6,
                           "monitor": s7},
                "elapsed": elapsed, "stats": stats,
                "ledger_writes": led.write_count,
                "ledger_write_seconds": led.write_seconds,
                "digest_seconds": DIGEST_STATS["seconds"],
                "digest_calls": int(DIGEST_STATS["calls"])}


# --------------------------------------------------------------------------
# optional Prefect flow — same functions, scheduled
# --------------------------------------------------------------------------
try:
    from prefect import flow, task

    @task(name="ingest")
    def _t_ingest(cfg, path):
        with ThreadLedger(path) as led:
            return s1_ingest.run(cfg, led)

    @task(name="clean")
    def _t_clean(cfg, path, raw):
        with ThreadLedger(path) as led:
            return s2_clean.run(cfg, led, raw)

    @task(name="features")
    def _t_features(cfg, path, clean):
        with ThreadLedger(path) as led:
            return s3_features.run(cfg, led, clean)

    @task(name="train")
    def _t_train(cfg, path, feats):
        with ThreadLedger(path) as led:
            return s4_train.run(cfg, led, feats)

    @task(name="promote")
    def _t_promote(cfg, path, models):
        with ThreadLedger(path) as led:
            return s5_evaluate.run(cfg, led, models)

    @task(name="monitor")
    def _t_monitor(cfg, path, feats, raw):
        with ThreadLedger(path) as led:
            s6_serve.run(cfg, led, feats)
            return s7_monitor.run(cfg, led, feats, raw)

    @flow(name="digital-thread-analytics")
    def prefect_flow() -> dict[str, Any]:
        cfg = load_config()
        path = cfg["paths"]["ledger"]
        s1 = _t_ingest(cfg, path)
        s2 = _t_clean(cfg, path, s1["raw"])
        s3 = _t_features(cfg, path, s2["clean"])
        s4 = _t_train(cfg, path, s3["features"])
        s5 = _t_promote(cfg, path, s4["models"])
        s7 = _t_monitor(cfg, path, s3["features"], s1["raw"])
        return {"promote": s5, "monitor": s7}

except ImportError:                                          # pragma: no cover
    prefect_flow = None                                      # type: ignore


if __name__ == "__main__":
    run_pipeline()
