"""Stage 1 — ingestion and validation.

Reads the raw dataset, fingerprints it, runs schema and quality checks, and
records both the dataset and the validation outcome in the ledger. The
validation report is a first-class node: "this data passed these checks on this
date" is exactly the kind of claim an audit asks for.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from thread import ThreadLedger, code_rev, environment_digest, environment_report, file_digest

from .common import banner, dataset_source, ensure_dirs, fetch_dataset, load_config


def validate(df: pd.DataFrame, rules: dict[str, Any]) -> dict[str, Any]:
    """A small, explicit expectation suite.

    Great Expectations or Pandera would do this in production; the point here
    is that whatever runs the checks, the *outcome* lands in the ledger in a
    tool-independent shape.
    """
    checks: list[dict[str, Any]] = []

    missing = [c for c in rules["required_columns"] if c not in df.columns]
    checks.append({"check": "required_columns_present", "passed": not missing,
                   "detail": f"missing={missing}" if missing else "all present"})

    expected = rules.get("expected_rows")
    if expected:
        checks.append({"check": "row_count", "passed": len(df) == expected,
                       "detail": f"{len(df)} rows (expected {expected})"})

    null_frac = float(df.isna().mean().max()) if len(df.columns) else 0.0
    checks.append({"check": "null_fraction",
                   "passed": null_frac <= rules["max_null_fraction"],
                   "detail": f"max null fraction {null_frac:.4f}"})

    dup_frac = float(df.duplicated().mean())
    checks.append({"check": "duplicate_fraction",
                   "passed": dup_frac <= rules["max_duplicate_fraction"],
                   "detail": f"{dup_frac:.4f}"})

    for col, (lo, hi) in (rules.get("ranges") or {}).items():
        if col not in df.columns:
            checks.append({"check": f"range[{col}]", "passed": False,
                           "detail": "column absent"})
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        out_of_range = int(((series < lo) | (series > hi)).sum())
        checks.append({"check": f"range[{col}]", "passed": out_of_range == 0,
                       "detail": f"{out_of_range} values outside [{lo}, {hi}]"})

    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["passed"]),
            "checks": checks}


def run(cfg: dict[str, Any], led: ThreadLedger) -> dict[str, str]:
    ensure_dirs(cfg)
    banner("stage 1 · ingestion & validation")

    with led.run("ingest", code_rev=code_rev("."),
                 environment=environment_digest(),
                 source=cfg["dataset"]["url"]) as run_h:

        csv_path = fetch_dataset(cfg)
        origin = dataset_source(cfg)
        digest = file_digest(csv_path)
        df = pd.read_csv(csv_path)

        raw = run_h.node("dataset", f"{cfg['dataset']['name']}-raw",
                         version=digest[:12], digest=digest,
                         path=csv_path, rows=len(df), columns=len(df.columns),
                         source=cfg["dataset"]["url"] if origin == "uci"
                         else "generated from the documented AI4I 2020 procedure",
                         origin=origin,
                         column_names=list(df.columns),
                         environment=environment_report())
        run_h.produced(raw)
        print(f"   raw dataset   {len(df)} rows x {len(df.columns)} cols  "
              f"sha256:{digest[:12]}  [{origin}]")
        if origin != "uci":
            print("   ! this run used a specification replica, not the UCI file")

        report = validate(df, cfg["validation"])
        val = run_h.node("validation", f"{cfg['dataset']['name']}-expectations",
                         version=digest[:12],
                         digest=f"val-{digest[:12]}",
                         passed=report["passed"], checks=report["n_checks"],
                         failed=report["n_failed"], detail=report["checks"])
        run_h.edge(val, raw, "VALIDATES")
        state = "PASSED" if report["passed"] else "FAILED"
        print(f"   validation    {state}  "
              f"({report['n_checks'] - report['n_failed']}/{report['n_checks']} checks)")
        for c in report["checks"]:
            if not c["passed"]:
                print(f"     ! {c['check']}: {c['detail']}")

        return {"raw": raw, "validation": val}


if __name__ == "__main__":
    cfg = load_config()
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        run(cfg, led)
