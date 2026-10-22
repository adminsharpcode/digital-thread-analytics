"""Stage 5 — comparison, promotion and registry.

Picks the best candidate on the configured primary metric, checks it against
the promotion gate, and records a `deployment` node linked to the winning model
by a PROMOTED_TO edge. Because the ledger is append-only, a later promotion
does not erase this one: the deployment history is itself a queryable trail.
"""

from __future__ import annotations

import json
import os
from typing import Any

from thread import ThreadLedger, code_rev, environment_digest

from .common import banner, ensure_dirs, load_config


def run(cfg: dict[str, Any], led: ThreadLedger,
        models: dict[str, str]) -> dict[str, Any]:
    ensure_dirs(cfg)
    banner("stage 5 · evaluation & promotion")

    metric = cfg["train"]["primary_metric"]
    gate = cfg["evaluate"]["promote_if_better_than"]

    ranked = []
    for name, nid in models.items():
        node = led.get_node(nid)
        if node is None:
            continue
        ranked.append((float(node.attrs.get(metric, 0.0)), name, nid, node))
    if not ranked:
        raise RuntimeError("no model nodes to evaluate")
    ranked.sort(reverse=True)

    print(f"   ranking on    {metric}")
    for score, name, _nid, _n in ranked:
        print(f"     {name:<20} {score:.4f}")

    best_score, best_name, best_id, best_node = ranked[0]
    if best_score < gate:
        print(f"   gate          FAILED ({best_score:.4f} < {gate}) — nothing promoted")
        return {"promoted": None, "winner": best_name, "score": best_score}

    with led.run("promote", code_rev=code_rev("."),
                 environment=environment_digest(),
                 primary_metric=metric, gate=gate) as run_h:

        existing = led.find(node_type="deployment")
        version = f"prod-{len(existing) + 1:02d}"
        dep = run_h.node("deployment", "prediction-service", version=version,
                         digest=f"{version}-{best_node.digest}",
                         model=best_name, model_digest=best_node.digest,
                         model_path=best_node.attrs.get("path"),
                         primary_metric=metric, score=best_score,
                         gate=gate, status="active")
        run_h.edge(dep, best_id, "PROMOTED_FROM", reason=f"best {metric}")
        run_h.produced(dep)

        record = {"deployment": version, "model": best_name,
                  metric: best_score, "runner_up": ranked[1][1] if len(ranked) > 1 else None}
        with open(os.path.join(cfg["paths"]["reports"], "promotion.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)

        print(f"   promoted      {best_name} -> deployment {version} "
              f"({metric}={best_score:.4f})")
        return {"promoted": dep, "winner": best_name, "score": best_score,
                "version": version}


if __name__ == "__main__":
    cfg = load_config()
    with ThreadLedger(cfg["paths"]["ledger"]) as led:
        found = {n.name: n.id for n in led.find(node_type="model")}
        if not found:
            raise SystemExit("run stage 4 first")
        run(cfg, led, found)
