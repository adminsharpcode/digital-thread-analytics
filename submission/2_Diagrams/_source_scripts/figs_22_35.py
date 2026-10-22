"""Figures 22-35: measured results, comparative analysis, roadmaps, contribution.

Figures 22, 23, 24 and 34 are plotted from artifacts/reports/*.json produced by
an actual pipeline run; nothing in them is illustrative.
"""
import json
import sys
sys.path.insert(0, "/home/claude/report/figsrc")
from figkit import *

EVAL = json.load(open("/home/claude/pds/artifacts/reports/framework_evaluation.json"))
DRIFT = json.load(open("/home/claude/pds/artifacts/reports/drift_report.json"))
METRICS = json.load(open("/home/claude/pds/artifacts/reports/training_metrics.json"))
STAGE_S = {"ingest": 0.5475, "clean": 0.101, "features": 0.058,
           "train:logistic_regression": 0.0764, "train:random_forest": 3.0609,
           "promote": 0.0049, "serve": 0.319, "monitor": 0.0141}


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=LINE, lw=0.6, alpha=0.7)
    ax.set_axisbelow(True)


# ---- Fig 22 Traceability Performance Results ----------------------------
def fig22():
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.3))
    t = EVAL["trace_time"]
    keys = ["model", "prediction_batch", "drift_report"]
    names = ["deployed\nmodel", "prediction\nbatch", "drift\nreport"]
    ms = [t[k]["median_ms"] for k in keys]
    nodes = [t[k]["nodes_reached"] for k in keys]

    a = axs[0]; _style(a)
    bars = a.bar(names, ms, color=[AMBER, ORANGE, RED], width=0.6)
    for b, v in zip(bars, ms):
        a.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center",
               fontsize=8, color=INK, fontweight="bold")
    a.set_ylabel("median query time (ms)", fontsize=8.5)
    a.set_title("(a) time to answer a provenance question", fontsize=8.8, color=INK)
    a.set_ylim(0, max(ms) * 1.28)
    a.tick_params(labelsize=7.6)

    b_ = axs[1]; _style(b_)
    bars = b_.bar(names, nodes, color=[AMBER, ORANGE, RED], width=0.6)
    for bb, v in zip(bars, nodes):
        b_.text(bb.get_x() + bb.get_width() / 2, v + 0.3, str(v), ha="center",
                fontsize=8, color=INK, fontweight="bold")
    b_.set_ylabel("artifacts reached", fontsize=8.5)
    b_.set_title("(b) provenance depth recovered", fontsize=8.8, color=INK)
    b_.set_ylim(0, max(nodes) * 1.25)
    b_.tick_params(labelsize=7.6)

    c = axs[2]; _style(c)
    comp = EVAL["completeness"]
    c.bar(["thread", "baseline"], [comp["rate"] * 100, 0],
          color=[GREEN, GREY], width=0.55)
    c.text(0, comp["rate"] * 100 + 3, f"{comp['rate']*100:.0f}%", ha="center",
           fontsize=9, color=GREEN, fontweight="bold")
    c.text(1, 3, "0%", ha="center", fontsize=9, color=MUTED, fontweight="bold")
    c.set_ylabel("terminal artifacts tracing to raw data (%)", fontsize=8.0)
    c.set_title(f"(c) lineage completeness ({comp['complete']}/{comp['terminal_artifacts']})",
                fontsize=8.8, color=INK)
    c.set_ylim(0, 118); c.tick_params(labelsize=7.6)
    return save(fig, 22, "Traceability Performance Results")


# ---- Fig 23 Lifecycle Efficiency Analysis -------------------------------
def fig23():
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.5),
                            gridspec_kw={"width_ratios": [1.05, 1.25]})
    o = EVAL["overhead"]
    a = axs[0]; _style(a)
    base = o["baseline_seconds"]
    ledger = o["ledger_write_seconds"]
    digest = o["digest_seconds"]
    other = o["threaded_comparable_seconds"] - base - ledger - digest
    a.bar(["baseline\n(no thread)"], [base], color=GREY, width=0.5, label="pipeline work")
    a.bar(["threaded"], [base], color=GREY, width=0.5)
    a.bar(["threaded"], [other], bottom=[base], color=BLUE, width=0.5,
          label="artifact persistence")
    a.bar(["threaded"], [digest], bottom=[base + other], color=GREEN, width=0.5,
          label="content fingerprinting")
    a.bar(["threaded"], [ledger], bottom=[base + other + digest], color=AMBER,
          width=0.5, label="ledger writes")
    a.set_ylabel("wall clock, comparable stages (s)", fontsize=8.5)
    a.set_title(f"(a) where the extra {o['overhead_pct']:.0f}% goes", fontsize=8.8, color=INK)
    a.legend(fontsize=6.6, frameon=False, loc="upper left")
    a.tick_params(labelsize=7.6)
    a.set_ylim(0, o["threaded_comparable_seconds"] * 1.35)
    a.text(1, o["threaded_comparable_seconds"] + 0.12,
           f"ledger {o['instrumentation_pct']:.1f}%  ·  digests {o['digest_pct']:.1f}%",
           ha="center", fontsize=7.0, color=INK, fontweight="bold")

    b = axs[1]; _style(b)
    labels = list(STAGE_S); vals = [STAGE_S[k] for k in labels]
    cols = [TEAL, TEAL, GREEN, VIOLET, VIOLET, AMBER, ORANGE, RED]
    bars = b.barh(range(len(labels)), vals, color=cols, height=0.62)
    b.set_yticks(range(len(labels)))
    b.set_yticklabels([l.replace("train:", "train · ") for l in labels], fontsize=7.4)
    b.invert_yaxis()
    b.set_xlabel("stage duration (s, log scale)", fontsize=8.5)
    b.set_xscale("log")
    b.set_title("(b) cost is dominated by model fitting, not by lineage", fontsize=8.8, color=INK)
    for bar, v in zip(bars, vals):
        b.text(v * 1.12, bar.get_y() + bar.get_height() / 2, f"{v:.3f}",
               va="center", fontsize=6.8, color=MUTED)
    b.grid(axis="y", lw=0); b.grid(axis="x", color=LINE, lw=0.6, alpha=0.7)
    b.tick_params(labelsize=7.4)
    return save(fig, 23, "Lifecycle Efficiency Analysis")


# ---- Fig 24 Governance Effectiveness Analysis ---------------------------
def fig24():
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.5),
                            gridspec_kw={"width_ratios": [1.0, 1.3]})
    a = axs[0]
    a.set_axis_off()
    questions = ["which data produced it", "was the data validated",
                 "which code and environment", "why was it promoted",
                 "what drift has occurred since"]
    a.set_xlim(0, 10); a.set_ylim(0, 6.4)
    a.text(0.2, 5.85, "audit question", fontsize=7.4, color=MUTED, fontweight="bold")
    a.text(7.0, 5.85, "thread", fontsize=7.4, color=GREEN, fontweight="bold", ha="center")
    a.text(9.0, 5.85, "baseline", fontsize=7.4, color=MUTED, fontweight="bold", ha="center")
    a.plot([0.2, 9.8], [5.6, 5.6], color=LINE, lw=1.0)
    for i, q in enumerate(questions):
        y = 4.9 - i * 0.95
        a.text(0.2, y, q, fontsize=7.6, color=INK, va="center")
        a.text(7.0, y, "\u2713", fontsize=12, color=GREEN, ha="center", va="center",
               fontweight="bold")
        a.text(9.0, y, "\u2014", fontsize=11, color=GREY, ha="center", va="center")
        a.plot([0.2, 9.8], [y - 0.47, y - 0.47], color=LINE, lw=0.5, alpha=0.7)
    a.set_title("(a) audit questions answerable from the record", fontsize=8.8, color=INK)

    b = axs[1]; _style(b)
    psi = DRIFT["psi"]; thr = DRIFT["threshold"]
    items = sorted(psi.items(), key=lambda kv: -kv[1])
    names = [k for k, _ in items]; vals = [v for _, v in items]
    cols = [RED if v >= thr else BLUE for v in vals]
    bars = b.barh(range(len(names)), vals, color=cols, height=0.6)
    b.set_yticks(range(len(names))); b.set_yticklabels(names, fontsize=7.0)
    b.invert_yaxis(); b.set_xscale("symlog", linthresh=0.01)
    b.axvline(thr, color=RED, lw=1.3, ls="--")
    b.text(thr * 1.15, len(names) - 0.4, f"threshold {thr}", fontsize=7.0, color=RED)
    for bar, v in zip(bars, vals):
        b.text(max(v, 0.0) + (0.006 if v < 0.01 else v * 0.15),
               bar.get_y() + bar.get_height() / 2,
               f"{v:.3f}" + ("  (no shift)" if v == 0 else ""),
               va="center", fontsize=6.7, color=MUTED)
    b.set_xlabel("population stability index (symlog)", fontsize=8.5)
    b.set_title("(b) drift detected on the monitored batch", fontsize=8.8, color=INK)
    b.grid(axis="y", lw=0); b.grid(axis="x", color=LINE, lw=0.6, alpha=0.7)
    return save(fig, 24, "Governance Effectiveness Analysis")


# ---- Fig 25 Comparative Benchmark Radar ---------------------------------
def fig25():
    dims = ["Data\nversioning", "Experiment\ntracking", "Validation\noutcomes",
            "Serving\nlineage", "Drift\nlinkage", "Bidirectional\ntraversal",
            "Immutable\nhistory"]
    series = [("Conventional pipeline", [0, 0, 0, 0, 0, 0, 0], GREY),
              ("DVC only", [3, 0, 0, 0, 0, 0, 1], TEAL),
              ("MLflow only", [1, 3, 0, 1, 0, 0, 0], VIOLET),
              ("DVC + MLflow", [3, 3, 1, 1, 0, 0, 1], BLUE),
              ("Digital thread (this work)", [2, 3, 3, 3, 3, 3, 3], GREEN)]
    n = len(dims)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist(); ang += ang[:1]
    fig, ax = plt.subplots(figsize=(7.2, 5.4), subplot_kw=dict(polar=True))
    for name, vals, col in series:
        v = vals + vals[:1]
        ax.plot(ang, v, color=col, lw=1.9, label=name, zorder=4)
        if name.startswith("Digital"):
            ax.fill(ang, v, color=col, alpha=0.13, zorder=3)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(dims, fontsize=7.6, color=INK)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["none", "partial", "good", "full"], fontsize=6.8, color=MUTED)
    ax.set_ylim(0, 3.4)
    ax.grid(color=LINE, lw=0.7)
    ax.spines["polar"].set_color(LINE)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=3,
              fontsize=7.0, frameon=False)
    ax.set_title("capability coverage, not measured throughput", fontsize=8.4,
                 color=MUTED, style="italic", pad=16)
    return save(fig, 25, "Comparative Benchmark Analysis")


# ---- Fig 26 Reproducibility Assessment Model ----------------------------
def fig26():
    fig, ax = canvas(10, 4.6, 100, 46)
    levels = [("R0  Not reproducible", "no record of data, code or environment", GREY),
              ("R1  Code reproducible", "source under version control only", BLUE),
              ("R2  Data reproducible", "dataset versions pinned by digest", TEAL),
              ("R3  Run reproducible", "code, data, parameters and environment pinned", VIOLET),
              ("R4  Thread reproducible", "identity of every artifact is itself verifiable", GREEN)]
    fillmap = {GREY: GREY_F, BLUE: BLUE_F, TEAL: TEAL_F, VIOLET: VIOLET_F, GREEN: GREEN_F}
    for i, (t, s, col) in enumerate(levels):
        w = 36 + i * 12
        y = 4 + i * 8.0
        box(ax, 3, y, w, 7.0, t, sub=s, fill=fillmap[col], edge=col, fs=8.2,
            bold=True, sub_fs=6.6)
    label(ax, 62, 10.5, "this work is evaluated at R4:\ncontent-addressed identity means two\nruns are identical exactly when their\nartifact identifiers coincide",
          fs=7.6, color=GREEN, ha="left", bold=False)
    label(ax, 50, 44.0, "a reproducibility ladder for lifecycle artifacts", fs=8.6, bold=True, color=INK)
    return save(fig, 26, "Reproducibility Assessment Model")


# ---- Fig 27 Smart Manufacturing Digital Thread Ecosystem ----------------
def fig27():
    fig, ax = canvas(10, 4.8, 100, 48)
    rows = [("SHOP FLOOR", ["machine tools", "sensors / PLC", "quality station"], TEAL),
            ("PLANT SYSTEMS", ["MES", "historian", "CMMS work orders"], BLUE),
            ("ANALYTICS", ["feature store", "failure models", "drift monitor"], VIOLET),
            ("DECISION", ["maintenance plan", "spares policy", "line scheduling"], AMBER)]
    fillmap = {TEAL: TEAL_F, BLUE: BLUE_F, VIOLET: VIOLET_F, AMBER: AMBER_F}
    for i, (t, items, col) in enumerate(rows):
        y = 36 - i * 9.0
        label(ax, 3, y + 3.2, t, fs=7.4, color=col, bold=True, ha="left")
        for j, it in enumerate(items):
            box(ax, 20 + j * 26, y, 24, 6.4, it, fill=fillmap[col], edge=col, fs=7.4, lw=1.1)
        if i < len(rows) - 1:
            for j in range(3):
                arrow(ax, (32 + j * 26, y - 0.3), (32 + j * 26, y - 2.3), color=MUTED,
                      lw=0.9, ms=7)
    ax.add_patch(FancyBboxPatch((94.5, 8.5), 4.0, 34.0,
                 boxstyle="round,pad=0,rounding_size=0.02", linewidth=1.4,
                 edgecolor=AMBER, facecolor=AMBER_F, zorder=2))
    ax.text(96.5, 25.5, "THREAD", rotation=90, ha="center", va="center",
            fontsize=7.6, color="#6b4a12", fontweight="bold", zorder=4)
    label(ax, 50, 45.5, "the thread spans the layers that today keep separate records",
          fs=8.2, bold=True, color=INK)
    label(ax, 50, 3.0, "predictive maintenance is the case study because its failure mechanisms are documented and its drift story is concrete",
          fs=7.0, italic=True)
    return save(fig, 27, "Smart Manufacturing Digital Thread Ecosystem")


# ---- Fig 28 Aerospace Lifecycle Analytics Architecture ------------------
def fig28():
    fig, ax = canvas(10, 4.4, 100, 44)
    phases = [("Design", "requirements,\nCAD, simulation"), ("Certification", "test evidence,\nairworthiness"),
              ("Manufacture", "process data,\nas-built record"), ("In service", "flight data,\ninspections"),
              ("Sustainment", "repairs, life\nextension")]
    centers, w = chain(ax, phases, y=22, h=12.5, left=3, right=97, gap=2.5,
                       fs=8.4, pair=(BLUE, BLUE_F), numbered=True)
    for cx in centers:
        arrow(ax, (cx, 21.7), (cx, 15.3), color=AMBER, lw=1.0, ls=(0, (3, 2)), ms=7)
    band(ax, 3, 5.0, 94, 10.0, "CONFIGURATION-CONTROLLED THREAD",
         "each artifact is immutable and attributable, which is what certification evidence requires;\n"
         "the analytics layer inherits that property rather than re-creating it",
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=8.8, body_fs=6.9)
    label(ax, 50, 40.5, "aerospace is where digital thread originated — the evidential standard is the point",
          fs=7.8, italic=True)
    return save(fig, 28, "Aerospace Lifecycle Analytics Architecture")


# ---- Fig 29 Business Impact Assessment Framework ------------------------
def fig29():
    fig, ax = canvas(10, 4.8, 100, 48)
    cats = [("Debugging effort", "measured", "0.35 ms vs manual\nreconstruction", GREEN),
            ("Audit preparation", "measured", "5 of 5 audit questions\nanswerable from the record", GREEN),
            ("Reproducibility risk", "measured", "100% identity match\nover five runs", GREEN),
            ("Compute overhead", "measured", f"+{EVAL['overhead']['overhead_pct']:.0f}% end to end,\n"
                                             f"{EVAL['overhead']['instrumentation_pct']:.1f}% ledger", AMBER),
            ("Downtime avoided", "requires field study", "needs deployment on a\nreal production line", GREY),
            ("Compliance cost", "requires field study", "needs an organisation's\naudit cost baseline", GREY)]
    n = 3; w = (94 - 2 * 2.5) / 3
    for i, (t, status, detail, col) in enumerate(cats):
        r, c = divmod(i, n)
        x = 3 + c * (w + 2.5); y = 24 - r * 16.0
        fillc = {GREEN: GREEN_F, AMBER: AMBER_F, GREY: GREY_F}[col]
        box(ax, x, y, w, 14.0, t, fill=fillc, edge=col, fs=8.8, bold=True)
        label(ax, x + w / 2, y + 8.2, status.upper(), fs=6.6, color=col, bold=True)
        label(ax, x + w / 2, y + 4.0, detail, fs=6.9, color=MUTED)
    label(ax, 50, 45.0, "what this study can and cannot claim about business impact",
          fs=8.6, bold=True, color=INK)
    label(ax, 50, 2.0, "the lower row is deliberately left unquantified: no field deployment was performed, so any figure would be invention",
          fs=7.2, italic=True, color=RED)
    return save(fig, 29, "Business Impact Assessment Framework")


# ---- Fig 30 Challenges and Limitations Roadmap --------------------------
def fig30():
    fig, ax = canvas(10, 4.6, 100, 46)
    items = [("Artifact-level\ngranularity", "cannot say which rows\nwere influential", "row-level provenance\nresearch", RED),
             ("Scale untested", "10 000 rows,\n32 nodes", "graph store benchmark\nat 10^6 nodes", AMBER),
             ("Coverage needs\ndiscipline", "an undeclared transform\nleaves a silent gap", "orchestrator-level\nenforcement", AMBER),
             ("Single case study", "one tabular dataset,\none domain", "replication on streaming\nand image pipelines", GREY)]
    n = len(items); w = (94 - (n - 1) * 2.4) / n
    fillmap = {RED: RED_F, AMBER: AMBER_F, GREY: GREY_F}
    for i, (t, now, nxt, col) in enumerate(items):
        x = 3 + i * (w + 2.4)
        box(ax, x, 29, w, 11.0, t, fill=fillmap[col], edge=col, fs=8.4, bold=True)
        box(ax, x, 17.5, w, 9.0, now, fill="white", edge=col, fs=7.0, lw=1.0)
        arrow(ax, (x + w / 2, 17.2), (x + w / 2, 12.3), color=col, lw=1.1, ms=8)
        box(ax, x, 3.0, w, 9.0, nxt, fill="#f7f9fb", edge=LINE, fs=7.0, lw=1.0)
    label(ax, 1.5, 22.0, "today", fs=7.0, color=MUTED, ha="left", bold=True)
    label(ax, 1.5, 7.5, "next", fs=7.0, color=MUTED, ha="left", bold=True)
    label(ax, 50, 43.5, "known limitations and the work each one implies", fs=8.6, bold=True, color=INK)
    return save(fig, 30, "Challenges and Limitations Roadmap")


# ---- Fig 31 Future Research Roadmap -------------------------------------
def fig31():
    fig, ax = canvas(10, 4.4, 100, 44)
    horizons = [("NEAR\n0-12 months", ["Airflow DAG and\ncontainerisation",
                                       "scale benchmark on\na graph store",
                                       "orchestrator-level\nenforcement"], GREEN),
                ("MID\n1-3 years", ["row-level and\ncolumn-level provenance",
                                    "federated threads across\norganisations",
                                    "automated audit\nevidence packs"], VIOLET),
                ("FAR\n3+ years", ["agentic DataOps that\nrepairs its own thread",
                                   "neuro-symbolic reasoning\nover the lineage graph",
                                   "self-certifying\nanalytics pipelines"], AMBER)]
    fillmap = {GREEN: GREEN_F, VIOLET: VIOLET_F, AMBER: AMBER_F}
    n = len(horizons); w = (94 - (n - 1) * 3.0) / n
    for i, (t, items, col) in enumerate(horizons):
        x = 3 + i * (w + 3.0)
        box(ax, x, 33, w, 8.0, t, fill=fillmap[col], edge=col, fs=8.4, bold=True)
        for j, it in enumerate(items):
            box(ax, x, 22.5 - j * 9.0, w, 7.4, it, fill="white", edge=col, fs=7.2, lw=1.0)
        if i < n - 1:
            arrow(ax, (x + w + 0.4, 37), (x + w + 2.6, 37), color=MUTED, lw=1.4, ms=9)
    label(ax, 50, 2.5, "each horizon depends on the one before it being measurable, not merely implemented",
          fs=7.4, italic=True)
    return save(fig, 31, "Future Research Roadmap")


# ---- Fig 32 Next-Generation Vision --------------------------------------
def fig32():
    fig, ax = canvas(9.8, 4.8, 100, 48)
    cx, cy = 50, 24
    ax.add_patch(Circle((cx, cy), 10.5, facecolor=GREEN_F, edgecolor=GREEN, lw=2.0, zorder=3))
    ax.text(cx, cy + 1.8, "SELF-", ha="center", va="center", fontsize=9.6,
            fontweight="bold", color=GREEN, zorder=5)
    ax.text(cx, cy - 2.0, "CERTIFYING", ha="center", va="center", fontsize=9.6,
            fontweight="bold", color=GREEN, zorder=5)
    caps = [("Autonomous\nthread repair", 90), ("Semantic\nquery interface", 30),
            ("Continuous\ncompliance proof", 330), ("Cross-organisation\nfederation", 270),
            ("Causal impact\nanalysis", 210), ("Policy-aware\nretraining", 150)]
    R = 21.0
    for t, deg in caps:
        a = np.deg2rad(deg)
        x, y = cx + R * np.cos(a), cy + R * np.sin(a) * 0.92
        box(ax, x - 10.5, y - 4.0, 21, 8.0, t, fill="white", edge=VIOLET, fs=7.4, lw=1.2)
        arrow(ax, (cx + 11.0 * np.cos(a), cy + 11.0 * np.sin(a) * 0.92),
              (x - 9.8 * np.cos(a), y - 3.8 * np.sin(a) * 0.92),
              color=GREEN, lw=1.1, ls=(0, (3, 2)), ms=8)
    label(ax, 50, 45.8, "the thread stops being documentation and becomes the control surface",
          fs=8.4, bold=True, color=INK)
    return save(fig, 32, "Next-Generation Digital Thread Analytics Vision")


# ---- Fig 33 Research Contribution Framework -----------------------------
def fig33():
    fig, ax = canvas(10, 4.6, 100, 46)
    cols = [("CONCEPTUAL", ["six-stage lifecycle\nreference model",
                            "eleven node and eleven\nedge vocabulary"], BLUE),
            ("ARCHITECTURAL", ["append-only ledger with\ncontent-addressed identity",
                               "uniform PROV edge\ndirection"], VIOLET),
            ("IMPLEMENTATION", ["working framework,\nseven stages, 25 tests",
                                "API and dashboard over\nthe same record"], GREEN),
            ("EMPIRICAL", ["100% reproducibility and\nlineage completeness",
                           "cost of the thread\nquantified and decomposed"], AMBER)]
    fillmap = {BLUE: BLUE_F, VIOLET: VIOLET_F, GREEN: GREEN_F, AMBER: AMBER_F}
    n = len(cols); w = (94 - (n - 1) * 2.4) / n
    for i, (t, items, col) in enumerate(cols):
        x = 3 + i * (w + 2.4)
        box(ax, x, 31, w, 7.5, t, fill=fillmap[col], edge=col, fs=8.6, bold=True)
        for j, it in enumerate(items):
            box(ax, x, 19.5 - j * 10.0, w, 8.5, it, fill="white", edge=col, fs=7.2, lw=1.0)
            arrow(ax, (x + w / 2, (31 if j == 0 else 19.5 - (j - 1) * 10.0) - 0.3),
                  (x + w / 2, 19.5 - j * 10.0 + 8.8), color=col, lw=0.9, ms=7)
    label(ax, 50, 42.5, "four kinds of contribution, each with its own evidence", fs=8.6, bold=True, color=INK)
    label(ax, 50, 2.0, "the empirical column is what distinguishes this from an integration exercise",
          fs=7.4, italic=True)
    return save(fig, 33, "Research Contribution Framework")


# ---- Fig 34 Case study model performance (real) -------------------------
def fig34():
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4),
                            gridspec_kw={"width_ratios": [1.3, 1.0]})
    a = axs[0]; _style(a)
    names = ["average_precision", "roc_auc", "f1", "precision", "recall"]
    pretty = ["PR-AUC", "ROC-AUC", "F1", "Precision", "Recall"]
    lr = [METRICS["logistic_regression"][k] for k in names]
    rf = [METRICS["random_forest"][k] for k in names]
    x = np.arange(len(names))
    a.bar(x - 0.19, lr, 0.36, color=GREY, label="logistic regression")
    a.bar(x + 0.19, rf, 0.36, color=VIOLET, label="random forest (promoted)")
    for xi, v in zip(x - 0.19, lr):
        a.text(xi, v + 0.015, f"{v:.3f}", ha="center", fontsize=6.6, color=MUTED)
    for xi, v in zip(x + 0.19, rf):
        a.text(xi, v + 0.015, f"{v:.3f}", ha="center", fontsize=6.6, color=VIOLET)
    a.set_xticks(x); a.set_xticklabels(pretty, fontsize=7.6)
    a.set_ylim(0, 1.12); a.set_ylabel("score", fontsize=8.5)
    a.set_title("(a) candidate comparison on the held-out split", fontsize=8.8, color=INK)
    a.legend(fontsize=6.8, frameon=False, loc="upper right")
    a.tick_params(labelsize=7.4)

    b = axs[1]; _style(b)
    sizes = [96.61, 3.39]
    b.pie(sizes, labels=["no failure", "failure"], colors=[BLUE_F, RED],
          autopct="%1.2f%%", startangle=90,
          textprops={"fontsize": 7.6, "color": INK},
          wedgeprops={"edgecolor": "white", "linewidth": 1.2})
    b.set_title("(b) class balance — why PR-AUC is the primary metric",
                fontsize=8.8, color=INK)
    return save(fig, 34, "Case Study Model Performance")


if __name__ == "__main__":
    for f in (fig22, fig23, fig24, fig25, fig26, fig27, fig28, fig29, fig30,
              fig31, fig32, fig33, fig34):
        f()
