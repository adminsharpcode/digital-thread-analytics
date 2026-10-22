"""Render the thread as a self-contained HTML page.

No external libraries and no CDN: the page is one file of inline SVG, so it can
be opened from disk, attached to a report, or committed as evidence of a run.
Node placement is a simple layered (Sugiyama-style) layout — longest-path
layering, then barycentre ordering within each layer to reduce crossings.
"""

from __future__ import annotations

import html
import json
import os
from collections import defaultdict
from typing import Any

from .ledger import ThreadLedger

PALETTE = {
    "dataset": ("#e4ecf5", "#3d5a80"),
    "validation": ("#f3e4e4", "#9e4b4b"),
    "feature_set": ("#dfeee4", "#3f7350"),
    "code_rev": ("#eceff2", "#8b97a3"),
    "environment": ("#eceff2", "#8b97a3"),
    "run": ("#e8e2f2", "#5c4b8a"),
    "model": ("#e8e2f2", "#5c4b8a"),
    "evaluation": ("#f7f0e0", "#a9761f"),
    "deployment": ("#fbe7cf", "#b06d1d"),
    "prediction_batch": ("#fbe7cf", "#b06d1d"),
    "drift_report": ("#f9dcd6", "#9c4221"),
}

NODE_W, NODE_H = 190, 54
H_GAP, V_GAP = 110, 30
MARGIN = 40


def _layers(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """Longest-path layering over the DAG (cycles broken by visit order).

    Ledger edges point backwards in time, so they are reversed here: the
    picture should read left to right in the order things actually happened,
    with raw data on the left and drift reports on the right.
    """
    ids = {n["id"] for n in nodes}
    out = defaultdict(list)
    indeg = {i: 0 for i in ids}
    for e in edges:
        if e["src"] in ids and e["dst"] in ids:
            out[e["dst"]].append(e["src"])      # reversed
            indeg[e["src"]] += 1

    layer = {i: 0 for i in ids}
    queue = [i for i in ids if indeg[i] == 0]
    seen = set(queue)
    while queue:
        cur = queue.pop(0)
        for nxt in out[cur]:
            layer[nxt] = max(layer[nxt], layer[cur] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] <= 0 and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    for i in ids - seen:                   # anything left inside a cycle
        layer.setdefault(i, 0)
    return layer


def _order(by_layer: dict[int, list[str]], edges: list[dict]) -> None:
    """Two barycentre sweeps to cut edge crossings."""
    preds = defaultdict(list)
    for e in edges:
        preds[e["src"]].append(e["dst"])        # reversed, as in _layers
    for _ in range(2):
        for depth in sorted(by_layer):
            if depth == 0:
                continue
            above = {nid: i for i, nid in enumerate(by_layer[depth - 1])}
            def key(nid: str) -> float:
                ps = [above[p] for p in preds[nid] if p in above]
                return sum(ps) / len(ps) if ps else 1e9
            by_layer[depth].sort(key=key)


def build_svg(payload: dict[str, Any]) -> tuple[str, int, int]:
    nodes, edges = payload["nodes"], payload["edges"]
    if not nodes:
        return "<text x='20' y='40'>ledger is empty</text>", 400, 80

    layer = _layers(nodes, edges)
    by_layer: dict[int, list[str]] = defaultdict(list)
    for n in nodes:
        by_layer[layer[n["id"]]].append(n["id"])
    _order(by_layer, edges)

    pos: dict[str, tuple[float, float]] = {}
    for depth, ids in by_layer.items():
        x = MARGIN + depth * (NODE_W + H_GAP)
        for row, nid in enumerate(ids):
            pos[nid] = (x, MARGIN + row * (NODE_H + V_GAP))

    width = MARGIN * 2 + (max(by_layer) + 1) * (NODE_W + H_GAP) - H_GAP
    height = MARGIN * 2 + max(len(v) for v in by_layer.values()) * (NODE_H + V_GAP)

    index = {n["id"]: n for n in nodes}
    parts: list[str] = [
        "<defs><marker id='arrow' viewBox='0 0 10 10' refX='9' refY='5' "
        "markerWidth='7' markerHeight='7' orient='auto-start-reverse'>"
        "<path d='M 0 0 L 10 5 L 0 10 z' fill='#8b97a3'/></marker></defs>"
    ]

    for e in edges:
        if e["src"] not in pos or e["dst"] not in pos:
            continue
        # drawn in time order: from the dependency to the artifact
        x1, y1 = pos[e["dst"]]
        x2, y2 = pos[e["src"]]
        sx, sy = x1 + NODE_W, y1 + NODE_H / 2
        tx, ty = x2, y2 + NODE_H / 2
        mid = (sx + tx) / 2
        span = abs(layer[e["src"]] - layer[e["dst"]])
        faint = span > 1 or abs(sy - ty) > 3 * (NODE_H + V_GAP)
        parts.append(
            f"<path class='edge' d='M {sx:.0f} {sy:.0f} C {mid:.0f} {sy:.0f}, "
            f"{mid:.0f} {ty:.0f}, {tx:.0f} {ty:.0f}' fill='none' "
            f"stroke='#8b97a3' stroke-width='{0.7 if faint else 1.3}' "
            f"stroke-opacity='{0.45 if faint else 1}' "
            f"marker-end='url(#arrow)'>"
            f"<title>{html.escape(e['rel'])}</title></path>"
        )
        # long edges would litter the page with labels; their relation stays
        # available on hover
        if not faint:
            parts.append(
                f"<text class='elabel' x='{mid:.0f}' y='{(sy + ty) / 2 - 5:.0f}' "
                f"text-anchor='middle'>{html.escape(e['rel'])}</text>"
            )

    for nid, (x, y) in pos.items():
        n = index[nid]
        fill, stroke = PALETTE.get(n["type"], ("#f2f4f6", "#8b97a3"))
        label = n["name"]
        if len(label) > 25:
            label = label[:24] + "\u2026"
        ver = n.get("version") or ""
        if len(ver) > 28:
            ver = ver[:27] + "\u2026"
        attrs = json.dumps(n.get("attrs") or {}, indent=2, default=str)
        parts.append(
            f"<g class='node' data-type='{html.escape(n['type'])}'>"
            f"<title>{html.escape(n['type'])} · {html.escape(nid)}\n{html.escape(attrs)}</title>"
            f"<rect x='{x}' y='{y}' width='{NODE_W}' height='{NODE_H}' rx='6' "
            f"fill='{fill}' stroke='{stroke}' stroke-width='1.3'/>"
            f"<text class='ntype' x='{x + 10}' y='{y + 17}'>{html.escape(n['type'])}</text>"
            f"<text class='nname' x='{x + 10}' y='{y + 33}'>{html.escape(label)}</text>"
            f"<text class='nver' x='{x + 10}' y='{y + 46}'>{html.escape(ver)}</text>"
            f"</g>"
        )

    return "\n".join(parts), int(width), int(height)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thread Ledger</title>
<style>
  :root {{ --bg:#ffffff; --ink:#1f2933; --muted:#5b6875; --line:#e1e6eb; }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{ --bg:#14181d; --ink:#e8ecf0; --muted:#9aa7b4; --line:#2a3038; }}
  }}
  html, body {{ background: var(--bg); color: var(--ink); margin:0;
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  header {{ padding: 24px 28px 8px; }}
  h1 {{ margin:0 0 4px; font-size: 20px; letter-spacing:-0.01em; }}
  p.sub {{ margin:0; color: var(--muted); font-size: 13px; }}
  .wrap {{ overflow:auto; padding: 12px 28px 32px; }}
  svg {{ display:block; }}
  text {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; fill: var(--ink); }}
  .ntype {{ font-size: 9px; fill: var(--muted); text-transform: uppercase; letter-spacing:.06em; }}
  .nname {{ font-size: 12px; font-weight: 600; }}
  .nver  {{ font-size: 9.5px; fill: var(--muted); }}
  .elabel {{ font-size: 8.5px; fill: var(--muted); }}
  .legend {{ padding: 0 28px 28px; display:flex; flex-wrap:wrap; gap:10px; }}
  .chip {{ font-size:11px; padding:3px 9px; border-radius:99px; border:1px solid; }}
  @media (max-width: 640px) {{ header, .wrap, .legend {{ padding-left:16px; padding-right:16px; }} }}
</style></head>
<body>
<header>
  <h1>Thread Ledger</h1>
  <p class="sub">{n_nodes} nodes · {n_edges} edges · hover any node for its recorded attributes</p>
</header>
<div class="wrap">
<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
{svg}
</svg>
</div>
<div class="legend">{chips}</div>
</body></html>
"""


def write_html(led: ThreadLedger, out_path: str = "artifacts/thread.html") -> str:
    payload = led.to_dict()
    svg, w, h = build_svg(payload)
    stats = led.stats()
    chips = "".join(
        f"<span class='chip' style='background:{PALETTE[t][0]};"
        f"border-color:{PALETTE[t][1]};color:#1f2933'>{t} · {c}</span>"
        for t, c in sorted(stats["nodes"].items()) if t in PALETTE
    )
    page = TEMPLATE.format(svg=svg, w=w, h=h, chips=chips,
                           n_nodes=stats["n_nodes"], n_edges=stats["n_edges"])
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return out_path


def write_dot(led: ThreadLedger, out_path: str = "artifacts/thread.dot") -> str:
    """Graphviz export, for anyone who would rather lay it out themselves."""
    payload = led.to_dict()
    lines = ["digraph thread {", '  rankdir=LR;',
             '  node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=10];']
    for n in payload["nodes"]:
        fill = PALETTE.get(n["type"], ("#f2f4f6", "#8b97a3"))[0]
        label = f'{n["type"]}\\n{n["name"]}\\n{n.get("version") or ""}'
        lines.append(f'  "{n["id"]}" [label="{label}" fillcolor="{fill}"];')
    for e in payload["edges"]:
        lines.append(f'  "{e["src"]}" -> "{e["dst"]}" [label="{e["rel"]}" fontsize=8];')
    lines.append("}")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out_path
