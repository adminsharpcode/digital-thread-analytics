"""Command-line interface for interrogating the thread.

    python -m thread.query stats
    python -m thread.query show --type dataset
    python -m thread.query trace <node-id>
    python -m thread.query explain-model
    python -m thread.query impact <node-id>
    python -m thread.query export --out artifacts/thread.html

The `explain-model` and `trace` commands are the ones the evaluation measures:
they are the "time to answer a provenance question" that a conventional
pipeline cannot answer without manual archaeology.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from .ledger import ThreadLedger


def _fmt_node(n) -> str:
    extra = ""
    if n.attrs:
        keys = [k for k in ("rows", "columns", "status", "roc_auc", "f1", "psi",
                            "algorithm", "seconds", "passed") if k in n.attrs]
        if keys:
            extra = "  {" + ", ".join(f"{k}={n.attrs[k]}" for k in keys) + "}"
    return f"  {n.id}  {n.label}{extra}"


def cmd_stats(led: ThreadLedger, args: argparse.Namespace) -> int:
    s = led.stats()
    print(f"thread ledger: {s['n_nodes']} nodes, {s['n_edges']} edges\n")
    print("nodes by type")
    for k, v in sorted(s["nodes"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:<18} {v}")
    print("\nedges by relation")
    for k, v in sorted(s["edges"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:<18} {v}")
    return 0


def cmd_show(led: ThreadLedger, args: argparse.Namespace) -> int:
    nodes = led.find(node_type=args.type, name=args.name)
    if not nodes:
        print("no matching nodes")
        return 1
    for n in nodes:
        print(_fmt_node(n))
    return 0


def cmd_trace(led: ThreadLedger, args: argparse.Namespace) -> int:
    started = time.perf_counter()
    bundle = led.trace(args.node_id)
    elapsed = time.perf_counter() - started
    print(f"trace of {bundle['node']['label']}  ({bundle['node']['id']})")
    print(f"reached {bundle['nodes_reached']} upstream nodes "
          f"in {elapsed * 1000:.1f} ms\n")
    for ntype, entries in bundle["provenance"].items():
        print(f"{ntype}")
        for e in entries:
            print(f"  [{e['depth']}] {e['label']}  via {e['via']}")
    return 0


def cmd_impact(led: ThreadLedger, args: argparse.Namespace) -> int:
    started = time.perf_counter()
    rows = led.downstream(args.node_id)
    elapsed = time.perf_counter() - started
    node = led.get_node(args.node_id)
    label = node.label if node else args.node_id
    print(f"everything affected by {label}: {len(rows)} nodes "
          f"({elapsed * 1000:.1f} ms)\n")
    for n, rel, depth in rows:
        print(f"  [{depth}] {n.label}  via {rel}")
    return 0


def cmd_explain_model(led: ThreadLedger, args: argparse.Namespace) -> int:
    """The headline query: trace a deployed model back to its raw source."""
    model = led.latest("model", args.name) if args.name else led.latest("model")
    if model is None:
        print("no model recorded in the ledger yet — run the pipeline first")
        return 1
    started = time.perf_counter()
    bundle = led.trace(model.id)
    elapsed = time.perf_counter() - started

    prov = bundle["provenance"]
    upstream_ids = {e["id"] for group in prov.values() for e in group}

    print(f"model      {model.label}")
    for k, v in model.attrs.items():
        print(f"             {k}: {v}")
    print()
    for ntype in ("run", "feature_set", "dataset", "validation", "code_rev",
                  "environment", "evaluation"):
        for e in prov.get(ntype, []):
            attrs = {k: v for k, v in e["attrs"].items()
                     if k in ("rows", "columns", "algorithm", "status",
                              "passed", "checks", "roc_auc", "f1", "source")}
            tail = f"   {attrs}" if attrs else ""
            print(f"{ntype:<12} {e['label']}{tail}")
    # validation reports point AT the datasets they checked, so they sit
    # downstream of the data rather than upstream of the model; surface them
    # explicitly, because "was this data checked?" is the other half of the
    # provenance question
    checked = []
    for nid in upstream_ids:
        for n, rel, _d in led.downstream(nid, max_depth=1, rels=["VALIDATES"]):
            if n.type == "validation":
                checked.append(n)
    for v in checked:
        verdict = "passed" if v.attrs.get("passed") else "FAILED"
        print(f"{'validation':<12} {v.label}   {verdict} "
              f"{v.attrs.get('checks')} checks")
    if not checked:
        print(f"{'validation':<12} none recorded for the upstream data")

    print(f"\nanswered in {elapsed * 1000:.1f} ms across "
          f"{bundle['nodes_reached']} nodes")
    return 0


def cmd_export(led: ThreadLedger, args: argparse.Namespace) -> int:
    from .viz import write_html
    path = write_html(led, args.out)
    print(f"wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="thread.query",
                               description="interrogate the thread ledger")
    p.add_argument("--ledger", default="artifacts/thread_ledger.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats").set_defaults(fn=cmd_stats)

    s = sub.add_parser("show")
    s.add_argument("--type", default=None)
    s.add_argument("--name", default=None)
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("trace")
    s.add_argument("node_id")
    s.set_defaults(fn=cmd_trace)

    s = sub.add_parser("impact")
    s.add_argument("node_id")
    s.set_defaults(fn=cmd_impact)

    s = sub.add_parser("explain-model")
    s.add_argument("--name", default=None)
    s.set_defaults(fn=cmd_explain_model)

    s = sub.add_parser("export")
    s.add_argument("--out", default="artifacts/thread.html")
    s.set_defaults(fn=cmd_export)

    args = p.parse_args(argv)
    with ThreadLedger(args.ledger) as led:
        return int(args.fn(led, args))


if __name__ == "__main__":
    sys.exit(main())
