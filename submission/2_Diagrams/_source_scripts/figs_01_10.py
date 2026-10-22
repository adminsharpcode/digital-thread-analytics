"""Figures 1-10: context, problem framing, requirements, architecture, metadata."""
import sys
sys.path.insert(0, "/home/claude/report/figsrc")
from figkit import *


# ---- Fig 01 Evolution of Data Science Lifecycle Management ---------------
def fig01():
    fig, ax = canvas(10, 4.0, 100, 40)
    eras = [
        ("Era 1\n1990s-2000s", "Ad-hoc analysis", "spreadsheets, single\nanalyst, no versioning", GREY),
        ("Era 2\n2000s-2010s", "Scripted pipelines", "scripts and notebooks,\ncode in version control", BLUE),
        ("Era 3\n2010s-2020s", "MLOps tooling", "experiment tracking,\ndata versioning, CI/CD", VIOLET),
        ("Era 4\nemerging", "Threaded lifecycle", "one lineage record\nacross all stages", GREEN),
    ]
    n = len(eras); left, right, gap = 3.0, 97.0, 3.0
    w = (right - left - gap * (n - 1)) / n
    for i, (era, title, sub, col) in enumerate(eras):
        x = left + i * (w + gap)
        fillmap = {GREY: GREY_F, BLUE: BLUE_F, VIOLET: VIOLET_F, GREEN: GREEN_F}
        box(ax, x, 16, w, 18, "", fill=fillmap[col], edge=col)
        ax.text(x + w / 2, 30.6, era, ha="center", va="center", fontsize=7.4,
                color=col, fontweight="bold", zorder=5, linespacing=1.4)
        ax.text(x + w / 2, 25.4, title, ha="center", va="center", fontsize=9.6,
                color=INK, fontweight="bold", zorder=5)
        ax.text(x + w / 2, 20.4, sub, ha="center", va="center", fontsize=7.2,
                color=MUTED, zorder=5, linespacing=1.5)
        if i < n - 1:
            arrow(ax, (x + w + 0.4, 25), (x + w + gap - 0.4, 25), color=MUTED, lw=1.5, ms=10)
    # traceability trend underneath
    label(ax, 50, 12.2, "lifecycle traceability achieved", fs=8.0, bold=True, color=INK)
    xs = np.linspace(6, 94, 200)
    ys = 3.2 + 5.4 * (1 / (1 + np.exp(-(xs - 68) / 9)))
    ax.plot(xs, ys, color=GREEN, lw=2.2, zorder=4)
    ax.fill_between(xs, 2.8, ys, color=GREEN_F, zorder=2)
    label(ax, 14, 4.6, "effectively none", fs=6.8)
    label(ax, 86, 10.0, "end to end", fs=6.8, color=GREEN, bold=True)
    ax.plot([3, 97], [2.8, 2.8], color=LINE, lw=1.0, zorder=3)
    return save(fig, 1, "Evolution of Data Science Lifecycle Management")


# ---- Fig 02 Digital Thread Ecosystem Overview ---------------------------
def fig02():
    fig, ax = canvas(9.6, 6.0, 100, 60)
    cx, cy = 50, 31
    ax.add_patch(Circle((cx, cy), 11.5, facecolor=AMBER_F, edgecolor=AMBER, lw=2.0, zorder=3))
    ax.text(cx, cy + 2.0, "DIGITAL", ha="center", va="center", fontsize=10.5,
            fontweight="bold", color="#6b4a12", zorder=5)
    ax.text(cx, cy - 2.0, "THREAD", ha="center", va="center", fontsize=10.5,
            fontweight="bold", color="#6b4a12", zorder=5)
    sats = [
        ("Design &\nRequirements", 90, BLUE), ("Data\nSources", 38, TEAL),
        ("Production\n& Operations", 342, GREEN), ("Analytics\n& Models", 294, VIOLET),
        ("Service &\nMonitoring", 246, ORANGE), ("Governance\n& Audit", 198, RED),
        ("Stakeholder\nDecisions", 150, GREY),
    ]
    fillmap = {BLUE: BLUE_F, TEAL: TEAL_F, GREEN: GREEN_F, VIOLET: VIOLET_F,
               ORANGE: ORANGE_F, RED: RED_F, GREY: GREY_F}
    R = 23.0
    for text, deg, col in sats:
        a = np.deg2rad(deg)
        x, y = cx + R * np.cos(a), cy + R * np.sin(a) * 0.95
        box(ax, x - 9.5, y - 4.2, 19, 8.4, text, fill=fillmap[col], edge=col, fs=7.6, bold=True)
        ux, uy = np.cos(a), np.sin(a) * 0.95
        arrow(ax, (cx + 12.0 * ux, cy + 12.0 * uy), (x - 9.0 * ux, y - 4.0 * uy),
              color=AMBER, lw=1.2, ls=(0, (3, 2)), ms=8, style="<|-|>")
    label(ax, 50, 56.5, "every participant reads from and writes to the same authoritative record",
          fs=8.0, italic=True, color=MUTED)
    return save(fig, 2, "Digital Thread Ecosystem Overview")


# ---- Fig 03 Data Science Lifecycle Challenges Framework -----------------
def fig03():
    fig, ax = canvas(10, 5.2, 100, 52)
    band(ax, 3, 42, 94, 8, "SYMPTOM   a deployed model cannot be explained, reproduced or audited",
         None, fill=RED_F, edge=RED, title_color="#7a3318", fs=9.2)
    cats = [
        ("Siloed\nanalytics", "teams and tools keep\ntheir own records"),
        ("Fragmented\npipelines", "scripts and notebooks\nwith no shared state"),
        ("Poor\ntraceability", "no path from a prediction\nback to its inputs"),
        ("Governance\ncomplexity", "evidence assembled by\nhand for every audit"),
        ("Reproducibility\nfailure", "data, code and environment\nversions not captured"),
        ("Lifecycle\ndisconnect", "monitoring has no route\nback to retraining"),
    ]
    left, right, gap = 3.0, 97.0, 2.6
    w = (right - left - gap * 2) / 3
    for i, (t, s) in enumerate(cats):
        col, fillc = PAIRS[i % 6]
        r, c = divmod(i, 3)
        x = left + c * (w + gap)
        y = 24 - r * 14.5
        box(ax, x, y, w, 12.5, t, sub=s, fill=fillc, edge=col, fs=8.6, bold=True, sub_fs=6.9)
        arrow(ax, (x + w / 2, y + 12.5 + 0.3), (x + w / 2, 41.5), color=RED,
              lw=0.9, ls=(0, (2, 2)), ms=7)
    return save(fig, 3, "Data Science Lifecycle Challenges Framework")


# ---- Fig 04 Literature Taxonomy Framework -------------------------------
def fig04():
    fig, ax = canvas(10, 5.4, 100, 54)
    box(ax, 36, 45, 28, 7.5, "Lifecycle traceability\nliterature", fill=AMBER_F,
        edge=AMBER, fs=9.0, bold=True)
    branches = [
        ("Data-centric", ["Data versioning", "Data validation", "Data catalogs\n& metadata"], TEAL),
        ("Model-centric", ["Experiment\ntracking", "Model registry", "Feature stores"], VIOLET),
        ("Process-centric", ["Workflow\nprovenance", "DataOps /\nMLOps", "CI/CD for ML"], GREEN),
        ("Governance-centric", ["Explainability", "Audit &\ncompliance", "Documentation\nstandards"], RED),
    ]
    fillmap = {TEAL: TEAL_F, VIOLET: VIOLET_F, GREEN: GREEN_F, RED: RED_F}
    n = len(branches); left, right, gap = 2.0, 98.0, 2.4
    w = (right - left - gap * (n - 1)) / n
    for i, (title, leaves, col) in enumerate(branches):
        x = left + i * (w + gap)
        box(ax, x, 33, w, 7.0, title, fill=fillmap[col], edge=col, fs=8.4, bold=True)
        arrow(ax, (50, 44.7), (x + w / 2, 40.3), color=AMBER, lw=1.0, rad=0.0, ms=8)
        for j, leaf in enumerate(leaves):
            ly = 22 - j * 9.5
            box(ax, x + 1.5, ly, w - 3, 7.6, leaf, fill="#fbfcfd", edge=col, fs=7.4, lw=1.0)
            arrow(ax, (x + w / 2, (33 if j == 0 else 22 - (j - 1) * 9.5) - 0.3),
                  (x + w / 2, ly + 7.9), color=col, lw=0.9, ms=7)
    label(ax, 50, 1.6, "the gap this work addresses: no branch joins the other three into one queryable record",
          fs=7.6, italic=True)
    return save(fig, 4, "Literature Taxonomy Framework")


# ---- Fig 05 Requirements Engineering Framework --------------------------
def fig05():
    fig, ax = canvas(10, 5.0, 100, 50)
    fr = [("FR1 Traceability", "every artifact reachable\nfrom every other"),
          ("FR2 Interoperability", "tool-agnostic vocabulary,\nno hard dependency"),
          ("FR3 Explainability", "a prediction carries its\nown provenance"),
          ("FR4 Lifecycle continuity", "monitoring feeds back\ninto retraining")]
    nfr = [("NFR1 Integrity", "append-only, enforced\nby the storage layer"),
           ("NFR2 Low overhead", "instrumentation under\n5% of runtime"),
           ("NFR3 Scalability", "graph query cost grows\nsub-linearly with nodes"),
           ("NFR4 Auditability", "evidence exportable\nwithout the framework")]
    ax.add_patch(FancyBboxPatch((2, 18.6), 46, 29.4, boxstyle="round,pad=0,rounding_size=0.02",
                 linewidth=1.4, edgecolor=BLUE, facecolor="#f4f8fc", zorder=1))
    ax.add_patch(FancyBboxPatch((52, 18.6), 46, 29.4, boxstyle="round,pad=0,rounding_size=0.02",
                 linewidth=1.4, edgecolor=VIOLET, facecolor="#f6f4fb", zorder=1))
    label(ax, 4, 45.6, "FUNCTIONAL REQUIREMENTS", fs=8.6, color=BLUE, bold=True, ha="left")
    label(ax, 54, 45.6, "NON-FUNCTIONAL REQUIREMENTS", fs=8.6, color=VIOLET, bold=True, ha="left")
    for i, (t, sub) in enumerate(fr):
        box(ax, 4, 37.0 - i * 5.8, 42, 5.0, t, sub=sub, fill="white", edge=BLUE,
            fs=7.4, bold=True, sub_fs=6.2, lw=1.0)
    for i, (t, sub) in enumerate(nfr):
        box(ax, 54, 37.0 - i * 5.8, 42, 5.0, t, sub=sub, fill="white", edge=VIOLET,
            fs=7.4, bold=True, sub_fs=6.2, lw=1.0)
    ax.add_patch(FancyBboxPatch((2, 2), 96, 15, boxstyle="round,pad=0,rounding_size=0.02",
                 linewidth=1.4, edgecolor=GREEN, facecolor=GREEN_F, zorder=1))
    label(ax, 4, 14.6, "DESIGN RESPONSES IN THIS WORK", fs=8.6, color=GREEN, bold=True, ha="left")
    resp = ["Typed node and\nedge vocabulary", "Content-addressed\nidentity", "Append-only\nSQLite triggers",
            "Uniform PROV\nedge direction", "Lineage attached to\nevery API response"]
    w = (92 - 4 * 2.0) / 5
    for i, r in enumerate(resp):
        box(ax, 4 + i * (w + 2.0), 3.5, w, 8.0, r, fill="white", edge=GREEN, fs=7.4, lw=1.0)
    return save(fig, 5, "Requirements Engineering Framework")


# ---- Fig 06 CORE Digital Thread Analytics Architecture ------------------
def fig06():
    fig, ax = canvas(10.2, 6.0, 100, 60)
    stages = [("Ingestion &\nValidation", "schema + quality\nchecks, checksum"),
              ("Cleaning\n& EDA", "transforms,\nprofile report"),
              ("Feature\nEngineering", "features keyed to\nsource + code"),
              ("Training &\nTracking", "params, metrics,\nenv, commit SHA"),
              ("Evaluation\n& Registry", "compare, promote\nthe winner"),
              ("Deploy &\nMonitoring", "served version,\npredictions, drift")]
    centers, w = chain(ax, stages, y=38, h=14.5, left=3, right=97, gap=2.5,
                       fs=8.4, pair=(BLUE, BLUE_F), numbered=True)
    band(ax, 3, 16.5, 94, 12.5, "THREAD LEDGER   ·   append-only lineage graph (single source of truth)",
         "nodes:  dataset · validation · feature_set · code_rev · environment · run · model · evaluation · deployment · prediction_batch · drift_report\n"
         "edges:  DERIVED_FROM · VALIDATES · TRAINED_ON · BUILT_FROM · RAN_IN · PRODUCED_BY · EVALUATES · PROMOTED_FROM · SERVED_BY · OBSERVED_ON · TRIGGERS_RETRAIN",
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=9.2, body_fs=6.5)
    for cx in centers:
        arrow(ax, (cx - 1.5, 37.7), (cx - 1.5, 29.3), color=AMBER, lw=1.1, ls=(0, (3, 2)), ms=8)
        arrow(ax, (cx + 1.5, 29.3), (cx + 1.5, 37.7), color=AMBER, lw=1.1, ls=(0, (1, 2.4)), ms=8)
    label(ax, 0.2, 35.2, "emit  ↓", fs=6.8, color="#7a5a20", ha="left", italic=True)
    label(ax, 0.2, 32.2, "query  ↑", fs=6.8, color="#7a5a20", ha="left", italic=True)
    band(ax, 3, 5.0, 94, 8.5, "ORCHESTRATION   ·   Prefect / Airflow DAG",
         "schedules the stages, passes run context, retries on failure — every task wraps itself in a ledger transaction",
         fill=GREY_F, edge=GREY, title_color=INK, fs=9.0, body_fs=7.0)
    for cx in centers:
        arrow(ax, (cx, 13.8), (cx, 16.2), color=GREY, lw=1.0, ls=(0, (2, 2)), ms=7)
    arrow(ax, (centers[-1], 53.0), (centers[0], 53.0), color=RED, lw=1.8, rad=0.13, ms=11)
    label(ax, 50, 58.4, "feedback loop — drift above threshold reopens the thread and triggers retraining",
          fs=7.8, color=RED, bold=True, italic=True)
    return save(fig, 6, "Digital Thread Analytics Architecture")


# ---- Fig 07 Layered System Architecture ---------------------------------
def fig07():
    fig, ax = canvas(9.4, 6.2, 100, 62)
    layers = [
        ("L6  Decision & Presentation", "dashboard, prediction API, lineage explorer, exported evidence"),
        ("L5  Governance & Explainability", "validation verdicts, promotion gates, audit export, drift reports"),
        ("L4  Analytics & ML Lifecycle", "feature engineering, training, evaluation, registry, serving"),
        ("L3  Thread Ledger (metadata & lineage)", "append-only graph, content-addressed nodes, typed edges, traversal"),
        ("L2  Data Engineering & Transformation", "cleaning, profiling, schema evolution, artifact persistence"),
        ("L1  Data Acquisition & Integration", "file, batch, stream and IoT sources; checksum and schema capture"),
    ]
    pairs = [(GREY, GREY_F), (RED, RED_F), (VIOLET, VIOLET_F), (AMBER, AMBER_F),
             (GREEN, GREEN_F), (TEAL, TEAL_F)]
    top, h, gap = 58.0, 8.0, 1.6
    for i, (t, s) in enumerate(layers):
        y = top - (i + 1) * h - i * gap
        col, fillc = pairs[i]
        box(ax, 14, y, 72, h, t, sub=s, fill=fillc, edge=col, fs=8.6, bold=True, sub_fs=6.9)
    ax.add_patch(FancyBboxPatch((3.0, 4.0), 8.5, 54.0,
                 boxstyle="round,pad=0,rounding_size=0.02", linewidth=1.3,
                 edgecolor=BLUE, facecolor=BLUE_F, zorder=2))
    ax.text(7.25, 31, "CROSS-CUTTING\nconfiguration · identity · security",
            rotation=90, ha="center", va="center", fontsize=7.2, color=BLUE,
            fontweight="bold", zorder=4, linespacing=1.6)
    ax.add_patch(FancyBboxPatch((88.5, 4.0), 8.5, 54.0,
                 boxstyle="round,pad=0,rounding_size=0.02", linewidth=1.3,
                 edgecolor=AMBER, facecolor=AMBER_F, zorder=2))
    ax.text(92.75, 31, "THREAD LEDGER API\nemit · query · traverse",
            rotation=90, ha="center", va="center", fontsize=7.2, color="#6b4a12",
            fontweight="bold", zorder=4, linespacing=1.6)
    for i in range(len(layers)):
        y = top - (i + 1) * h - i * gap + h / 2
        arrow(ax, (86.3, y), (88.3, y), color=AMBER, lw=1.0, ms=7)
        arrow(ax, (13.8, y), (11.7, y), color=BLUE, lw=1.0, ms=7)
    return save(fig, 7, "Layered System Architecture")


# ---- Fig 08 Data Acquisition Framework ----------------------------------
def fig08():
    fig, ax = canvas(10, 5.0, 100, 50)
    srcs = [("Structured", "CSV, Parquet,\nRDBMS tables"), ("Semi-structured", "JSON, XML,\nlog files"),
            ("Unstructured", "documents,\nimages"), ("Streaming", "Kafka topics,\nevent buses"),
            ("IoT / sensor", "OPC-UA, MQTT,\nmachine telemetry")]
    n = len(srcs); w = (94 - 4 * 2.2) / n
    for i, (t, s) in enumerate(srcs):
        x = 3 + i * (w + 2.2)
        col, fillc = PAIRS[i % 6]
        box(ax, x, 37, w, 10.5, t, sub=s, fill=fillc, edge=col, fs=8.2, bold=True, sub_fs=6.8)
        arrow(ax, (x + w / 2, 36.7), (x + w / 2, 30.3), color=col, lw=1.1, ms=8)
    band(ax, 3, 21, 94, 9.0, "ACQUISITION LAYER",
         "connector · checksum (SHA-256) · schema capture · arrival timestamp · source attribution",
         fill=TEAL_F, edge=TEAL, fs=8.8, body_fs=7.0)
    arrow(ax, (50, 20.7), (50, 15.3), color=TEAL, lw=1.4, ms=9)
    band(ax, 3, 6.0, 94, 9.0, "VALIDATION GATE",
         "schema conformance · null and duplicate thresholds · value-range expectations · verdict written to the ledger as a validation node",
         fill=RED_F, edge=RED, fs=8.8, body_fs=7.0)
    label(ax, 50, 2.4, "a dataset enters the thread only once its checksum and validation verdict are recorded",
          fs=7.4, italic=True)
    return save(fig, 8, "Data Acquisition Framework")


# ---- Fig 09 Metadata and Lineage Architecture ---------------------------
def fig09():
    fig, ax = canvas(10, 5.2, 100, 52)
    band(ax, 3, 40, 94, 9.5, "CAPTURE",
         "stage decorators and the run context manager record what each stage read, produced and ran inside",
         fill=BLUE_F, edge=BLUE, fs=9.0, body_fs=7.0)
    arrow(ax, (50, 39.7), (50, 34.3), color=BLUE, lw=1.4, ms=9)
    band(ax, 3, 20, 94, 14.0, "STORE   ·   append-only SQLite graph", None,
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=9.0)
    inner = [("nodes", "id · type · name\nversion · digest · attrs"),
             ("edges", "src · dst · relation\nattrs · run id"),
             ("triggers", "UPDATE and DELETE\nrejected at the engine"),
             ("indices", "type · name\nsrc · dst")]
    w = (88 - 3 * 2.2) / 4
    for i, (t, s) in enumerate(inner):
        box(ax, 6 + i * (w + 2.2), 22, w, 8.4, t, sub=s, fill="white", edge=AMBER,
            fs=8.0, bold=True, sub_fs=6.5, lw=1.0)
    arrow(ax, (50, 19.7), (50, 14.3), color=AMBER, lw=1.4, ms=9)
    band(ax, 3, 4.0, 94, 10.0, "QUERY", None, fill=GREEN_F, edge=GREEN, fs=9.0)
    q = [("upstream()", "provenance"), ("downstream()", "impact"),
         ("trace()", "grouped bundle"), ("stats()", "ledger census"),
         ("to_dict()", "full export")]
    w2 = (88 - 4 * 2.2) / 5
    for i, (t, s) in enumerate(q):
        box(ax, 6 + i * (w2 + 2.2), 5.4, w2, 6.6, t, sub=s, fill="white", edge=GREEN,
            fs=7.8, bold=True, sub_fs=6.5, lw=1.0)
    return save(fig, 9, "Metadata and Lineage Architecture")


# ---- Fig 10 Knowledge Graph for Lifecycle Traceability ------------------
def fig10():
    fig, ax = canvas(10, 5.6, 100, 56)
    H, W = 8.0, 13.0
    c = [1.5, 22.5, 43.5, 64.5, 85.5]
    nodes = {
        "raw":   ("dataset\nraw v1", c[0], 44, W, BLUE, BLUE_F),
        "clean": ("dataset\nclean v1", c[1], 44, W, BLUE, BLUE_F),
        "feat":  ("feature_set\nv1", c[2], 44, W, GREEN, GREEN_F),
        "run":   ("run\ntrain:rf", c[3], 44, W, VIOLET, VIOLET_F),
        "model": ("model\nrandom_forest", c[4], 44, W, VIOLET, VIOLET_F),
        "code":  ("code_rev\nb7f1c2e", 56.0, 27, 11.0, GREY, GREY_F),
        "env":   ("environment\nlock", 69.0, 27, 11.0, GREY, GREY_F),
        "dep":   ("deployment\nprod-01", c[4], 27, W, ORANGE, ORANGE_F),
        "val":   ("validation\nreport", c[0], 12, W, RED, RED_F),
        "drift": ("drift_report\nPSI 2.56", c[2], 12, W, RED, RED_F),
        "pred":  ("prediction_batch\nweek-01", c[4], 12, W, ORANGE, ORANGE_F),
    }
    pos = {}
    for k, (t, x, y, w, col, fillc) in nodes.items():
        box(ax, x, y, w, H, t, fill=fillc, edge=col, fs=7.4, lw=1.3, r=0.025)
        pos[k] = (x, y, w, H)

    def anc(k, side, off=0.0):
        x, y, w, h = pos[k]
        return {"r": (x + w, y + h / 2 + off), "l": (x, y + h / 2 + off),
                "t": (x + w / 2 + off, y + h), "b": (x + w / 2 + off, y)}[side]

    rels = [("clean", "l", 0, "raw", "r", 0, "DERIVED_FROM", "above"),
            ("feat", "l", 0, "clean", "r", 0, "DERIVED_FROM", "above"),
            ("run", "l", 0, "feat", "r", 0, "TRAINED_ON", "above"),
            ("model", "l", 0, "run", "r", 0, "PRODUCED_BY", "above"),
            ("val", "t", -1.5, "raw", "b", -1.5, "VALIDATES", "right"),
            ("run", "b", -6.0, "code", "t", 0, "BUILT_FROM", "left"),
            ("run", "b", 0.0, "env", "t", 0, "RAN_IN", "right"),
            ("dep", "t", 0, "model", "b", 0, "PROMOTED_FROM", "right"),
            ("pred", "t", 0, "dep", "b", 0, "SERVED_BY", "right"),
            ("drift", "r", 0, "pred", "l", 0, "OBSERVED_ON", "above")]
    for a, sa, oa, b, sb, ob, text, where in rels:
        p1, p2 = anc(a, sa, oa), anc(b, sb, ob)
        arrow(ax, p1, p2, color=MUTED, lw=1.15, ms=8)
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        if where == "above":
            label(ax, mx, my + 1.6, text, fs=5.9, bold=True)
        elif where == "right":
            label(ax, mx + 1.1, my, text, fs=5.9, bold=True, ha="left")
        else:
            label(ax, mx - 1.1, my, text, fs=5.9, bold=True, ha="right")
    arrow(ax, anc("drift", "l"), anc("raw", "l"), color=RED, lw=1.5, ms=10, rad=-0.3)
    label(ax, 33, 25.0, "TRIGGERS_RETRAIN", fs=6.1, color=RED, bold=True)
    band(ax, 1.5, 53.2, 97, 4.2, "", None, fill="#f7f9fb", edge=LINE)
    label(ax, 3.2, 55.3, "edges point the way the ledger stores them — from an artifact to what it depended on   ·   "
                         "follow them outward for provenance, inward for impact",
          fs=7.2, color=INK, ha="left")
    return save(fig, 10, "Knowledge Graph for Lifecycle Traceability")


if __name__ == "__main__":
    for f in (fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08, fig09, fig10):
        f()
