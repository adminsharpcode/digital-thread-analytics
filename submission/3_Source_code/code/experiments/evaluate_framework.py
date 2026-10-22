"""The comparative study: what does the thread actually buy?

Four measurements, each defined so it can be reported without hand-waving.

1. Reproducibility rate. Run the threaded pipeline R times into fresh ledgers
   and compare the content-addressed identities of the raw dataset, the clean
   dataset, the feature set and each model. A run is reproducible when every
   one of those identities matches the first run's.

2. Lineage completeness. The fraction of terminal artifacts (models,
   deployments, prediction batches, drift reports) from which an upstream
   traversal reaches a raw dataset node. Anything less than 1.0 means the
   thread is broken somewhere.

3. Trace time. Wall-clock time to answer "which raw data, code revision and
   parameters produced this?" for the deployed model and for a served
   prediction batch. The baseline has no equivalent: the same question has to
   be answered by reading code and guessing, which is why it is reported as
   not available rather than as a number.

4. Overhead. Threaded wall clock against the no-thread baseline, plus the
   number of ledger writes and the size of the ledger on disk.

    python -m experiments.evaluate_framework --repeats 3
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thread import ThreadLedger                              # noqa: E402
from pipeline.common import load_config                      # noqa: E402
from pipeline.flow import run_pipeline                       # noqa: E402

TERMINALS = ("model", "deployment", "prediction_batch", "drift_report")


def _identity_fingerprint(led: ThreadLedger) -> dict[str, str]:
    """The content-addressed ids that must be stable across identical runs."""
    out: dict[str, str] = {}
    for ntype in ("dataset", "feature_set", "model"):
        for n in led.find(node_type=ntype):
            out[f"{ntype}:{n.name}"] = n.id
    return out


def measure_reproducibility(cfg: dict[str, Any], repeats: int) -> dict[str, Any]:
    print(f"\n[1/4] reproducibility over {repeats} independent runs")
    fingerprints: list[dict[str, str]] = []
    timings: list[float] = []
    tmp_root = tempfile.mkdtemp(prefix="dta-repro-")
    try:
        for i in range(repeats):
            ledger_path = os.path.join(tmp_root, f"run{i}.db")
            started = time.perf_counter()
            # silence stage output for the repeat runs
            buf, sys.stdout = sys.stdout, open(os.devnull, "w")
            try:
                run_pipeline(cfg, ledger_path=ledger_path)
            finally:
                sys.stdout.close()
                sys.stdout = buf
            timings.append(time.perf_counter() - started)
            with ThreadLedger(ledger_path) as led:
                fingerprints.append(_identity_fingerprint(led))
            print(f"      run {i + 1}: {len(fingerprints[-1])} addressable "
                  f"artifacts in {timings[-1]:.1f} s")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    reference = fingerprints[0]
    matches = [fp == reference for fp in fingerprints]
    rate = sum(matches) / len(matches)
    mismatched = sorted({k for fp in fingerprints for k in reference
                         if fp.get(k) != reference[k]})
    print(f"      reproducibility rate: {rate:.0%}"
          + (f"  (drift in {mismatched})" if mismatched else ""))
    return {"repeats": repeats, "rate": rate,
            "artifacts_compared": len(reference),
            "mismatched": mismatched,
            "mean_seconds": round(statistics.mean(timings), 2)}


def measure_completeness(led: ThreadLedger) -> dict[str, Any]:
    print("\n[2/4] lineage completeness")
    raw_ids = {n.id for n in led.find(node_type="dataset")
               if n.name.endswith("-raw")}
    checked, complete, broken = 0, 0, []
    for ntype in TERMINALS:
        for node in led.find(node_type=ntype):
            checked += 1
            reached = {n.id for n, _rel, _d in led.upstream(node.id)}
            if reached & raw_ids:
                complete += 1
            else:
                broken.append(node.label)
    rate = complete / checked if checked else 0.0
    print(f"      {complete}/{checked} terminal artifacts trace back to raw "
          f"data  ({rate:.0%})")
    for b in broken:
        print(f"      ! no path to raw data: {b}")
    return {"terminal_artifacts": checked, "complete": complete,
            "rate": rate, "broken": broken}


def measure_trace_time(led: ThreadLedger, trials: int = 20) -> dict[str, Any]:
    print("\n[3/4] time to answer a provenance question")
    results: dict[str, Any] = {}
    for label, ntype in (("deployed model", "model"),
                         ("prediction batch", "prediction_batch"),
                         ("drift report", "drift_report")):
        node = led.latest(ntype)
        if node is None:
            continue
        samples = []
        for _ in range(trials):
            t0 = time.perf_counter()
            bundle = led.trace(node.id)
            samples.append((time.perf_counter() - t0) * 1000)
        results[ntype] = {
            "label": label,
            "median_ms": round(statistics.median(samples), 2),
            "nodes_reached": bundle["nodes_reached"],
        }
        print(f"      {label:<18} {results[ntype]['median_ms']:.2f} ms median "
              f"over {trials} trials, {bundle['nodes_reached']} nodes reached")
    print("      baseline: not available — no lineage is recorded to query")
    return results


COMPARABLE_STAGES = ("ingest", "clean", "features",
                     "train:logistic_regression", "train:random_forest", "promote")


def _comparable_seconds(led: ThreadLedger) -> float:
    """Wall clock of only the stages the baseline script also performs.

    The threaded pipeline additionally serves two prediction batches and
    computes a drift report; the baseline does none of that. Timing the whole
    flow against the baseline would charge the thread for work the baseline
    never did, so the comparison is restricted to the stages both perform. The
    per-stage durations are read back out of the ledger's own outcome nodes.
    """
    total = 0.0
    for stage in COMPARABLE_STAGES:
        for n in led.find(node_type="evaluation", name=f"{stage}-outcome"):
            total += float(n.attrs.get("seconds", 0.0))
    return total


def measure_overhead(cfg: dict[str, Any], led: ThreadLedger,
                     ledger_writes: int, ledger_write_seconds: float,
                     digest_seconds: float, digest_calls: int,
                     ledger_path: str) -> dict[str, Any]:
    print("\n[4/4] cost of carrying the thread")

    # (a) direct measurement: time spent inside ledger writes
    comparable = _comparable_seconds(led)
    instrumentation_pct = (ledger_write_seconds / comparable * 100
                           if comparable else 0.0)
    digest_pct = digest_seconds / comparable * 100 if comparable else 0.0

    # (b) like-for-like against the no-thread script
    from baseline.run_baseline import main as baseline_main
    buf, sys.stdout = sys.stdout, open(os.devnull, "w")
    try:
        base = baseline_main()
    finally:
        sys.stdout.close()
        sys.stdout = buf
    base_seconds = float(base["elapsed"])
    overhead_pct = ((comparable - base_seconds) / base_seconds * 100
                    if base_seconds else 0.0)

    size_kb = os.path.getsize(ledger_path) / 1024 if os.path.exists(ledger_path) else 0.0

    print(f"      ledger writes    {ledger_writes} writes costing "
          f"{ledger_write_seconds:.3f} s")
    print(f"      instrumentation  {instrumentation_pct:.1f}% of the "
          f"{comparable:.2f} s spent on comparable stages")
    print(f"      fingerprinting   {digest_calls} content digests costing "
          f"{digest_seconds:.3f} s ({digest_pct:.1f}%)")
    print(f"      baseline script  {base_seconds:.2f} s for the same stages, "
          f"no lineage")
    print(f"      like-for-like    {overhead_pct:+.1f}%")
    print(f"      footprint        {size_kb:.0f} KB on disk")
    return {"baseline_seconds": round(base_seconds, 2),
            "threaded_comparable_seconds": round(comparable, 2),
            "overhead_pct": round(overhead_pct, 1),
            "ledger_writes": ledger_writes,
            "ledger_write_seconds": round(ledger_write_seconds, 3),
            "instrumentation_pct": round(instrumentation_pct, 2),
            "digest_seconds": round(digest_seconds, 3),
            "digest_calls": digest_calls,
            "digest_pct": round(digest_pct, 2),
            "ledger_kb": round(size_kb, 1),
            "comparable_stages": list(COMPARABLE_STAGES),
            "note": ("serving and monitoring are excluded from the comparison "
                     "because the baseline script does not perform them"),
            "baseline_scores": {k: v for k, v in base.items() if k != "elapsed"}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="evaluate the digital thread framework")
    ap.add_argument("--repeats", type=int, default=3,
                    help="independent pipeline runs for the reproducibility test")
    ap.add_argument("--out", default="artifacts/reports/framework_evaluation.json")
    args = ap.parse_args(argv)

    cfg = load_config()
    print("=" * 66)
    print("  FRAMEWORK EVALUATION — digital thread vs. conventional pipeline")
    print("=" * 66)

    # one reference run against the project ledger
    buf, sys.stdout = sys.stdout, open(os.devnull, "w")
    try:
        reference_run = run_pipeline(cfg)
    finally:
        sys.stdout.close()
        sys.stdout = buf

    repro = measure_reproducibility(cfg, args.repeats)
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        completeness = measure_completeness(led)
        trace = measure_trace_time(led)
        stats = led.stats()
        overhead = measure_overhead(cfg, led,
                                    reference_run["ledger_writes"],
                                    reference_run["ledger_write_seconds"],
                                    reference_run["digest_seconds"],
                                    reference_run["digest_calls"],
                                    cfg["paths"]["ledger"])

    report = {"reproducibility": repro, "completeness": completeness,
              "trace_time": trace, "overhead": overhead, "ledger": stats}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print("\n" + "=" * 66)
    print("  SUMMARY")
    print("=" * 66)
    print(f"  reproducibility rate      {repro['rate']:.0%} over {repro['repeats']} runs")
    print(f"  lineage completeness      {completeness['rate']:.0%} "
          f"({completeness['complete']}/{completeness['terminal_artifacts']} artifacts)")
    if "model" in trace:
        print(f"  trace a deployed model    {trace['model']['median_ms']:.2f} ms "
              f"(baseline: manual)")
    print(f"  instrumentation cost      {overhead['instrumentation_pct']:.2f}% "
          f"({overhead['ledger_write_seconds']:.3f} s of "
          f"{overhead['threaded_comparable_seconds']:.2f} s)")
    print(f"  like-for-like overhead    {overhead['overhead_pct']:+.1f}% "
          f"vs the no-thread script")
    print(f"  ledger footprint          {overhead['ledger_kb']:.0f} KB for "
          f"{stats['n_nodes']} nodes / {stats['n_edges']} edges")
    print(f"\n  written to {args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
