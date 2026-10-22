"""Figures 11-21: engineering, ML lifecycle, traceability, orchestration,
governance, decision support, testbed and evaluation framework."""
import sys
sys.path.insert(0, "/home/claude/report/figsrc")
from figkit import *


def fig11():
    fig, ax = canvas(10, 4.4, 100, 44)
    steps = [("Extract", "read raw file,\nSHA-256 checksum"),
             ("Validate", "schema, ranges,\nnulls, duplicates"),
             ("Transform", "drop identifiers\nand leakage columns"),
             ("Profile", "dtype census and\nsummary statistics"),
             ("Persist", "Parquet artifact,\ncontent digest"),
             ("Register", "dataset node +\nDERIVED_FROM edge")]
    centers, w = chain(ax, steps, y=22, h=13.0, left=3, right=97, gap=2.5,
                       fs=8.4, pair=(TEAL, TEAL_F), numbered=True)
    for cx in centers:
        arrow(ax, (cx, 21.7), (cx, 15.3), color=AMBER, lw=1.0, ls=(0, (3, 2)), ms=7)
    band(ax, 3, 5.0, 94, 10.0, "THREAD LEDGER",
         "each step appends what it consumed and produced; a failed step writes a failure outcome node rather than vanishing",
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=8.8, body_fs=7.0)
    label(ax, 50, 40.5, "schema evolution is detected by digest change, not by inspection",
          fs=7.6, italic=True)
    return save(fig, 11, "Data Engineering and Transformation Workflow")


def fig12():
    fig, ax = canvas(10, 5.2, 100, 52)
    band(ax, 3, 41, 94, 8.5, "FEATURE LAYER",
         "domain features derived from documented failure mechanisms; each definition versioned with the feature set",
         fill=GREEN_F, edge=GREEN, fs=8.8, body_fs=7.0)
    cands = [("Logistic regression", "balanced class weights\nstandardised inputs"),
             ("Random forest", "300 trees, depth 12\nbalanced subsample")]
    for i, (t, s) in enumerate(cands):
        box(ax, 8 + i * 44, 26, 40, 11.0, t, sub=s, fill=VIOLET_F, edge=VIOLET,
            fs=8.6, bold=True, sub_fs=6.9)
        arrow(ax, (28 + i * 44, 40.7), (28 + i * 44, 37.3), color=GREEN, lw=1.2, ms=8)
        arrow(ax, (28 + i * 44, 25.7), (28 + i * 44, 20.3), color=VIOLET, lw=1.2, ms=8)
    band(ax, 3, 11, 94, 9.0, "EVALUATION AND PROMOTION GATE",
         "ranked on average precision (PR-AUC); the winner must clear the configured gate before a deployment node is written",
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=8.8, body_fs=7.0)
    arrow(ax, (50, 10.7), (50, 7.3), color=AMBER, lw=1.3, ms=9)
    box(ax, 30, 1.5, 40, 5.8, "deployment  ·  prediction service",
        fill=ORANGE_F, edge=ORANGE, fs=8.4, bold=True)
    return save(fig, 12, "Machine Learning Lifecycle Architecture")


def fig13():
    fig, ax = canvas(10, 4.6, 100, 46)
    phases = [("Explore", GREEN), ("Engineer", GREEN), ("Train", VIOLET),
              ("Evaluate", VIOLET), ("Promote", AMBER), ("Serve", ORANGE), ("Observe", RED)]
    fillmap = {GREEN: GREEN_F, VIOLET: VIOLET_F, AMBER: AMBER_F, ORANGE: ORANGE_F, RED: RED_F}
    n = len(phases); w = (94 - (n - 1) * 2.0) / n
    cs = []
    for i, (t, col) in enumerate(phases):
        x = 3 + i * (w + 2.0)
        box(ax, x, 26, w, 8.5, t, fill=fillmap[col], edge=col, fs=8.6, bold=True)
        cs.append(x + w / 2)
        if i < n - 1:
            arrow(ax, (x + w + 0.3, 30.2), (x + w + 1.7, 30.2), color=MUTED, lw=1.3, ms=9)
    arts = ["profile\nreport", "feature_set\n+ definitions", "run\n+ params", "evaluation\nmetrics",
            "deployment\nrecord", "prediction\nbatch", "drift\nreport"]
    for cx, a in zip(cs, arts):
        arrow(ax, (cx, 25.7), (cx, 20.3), color=MUTED, lw=0.9, ls=(0, (2, 2)), ms=7)
        box(ax, cx - w / 2, 12.5, w, 7.8, a, fill="#fbfcfd", edge=LINE, fs=6.9, lw=1.0)
    label(ax, 50, 39.5, "each phase emits exactly one addressable artifact into the thread",
          fs=8.0, bold=True, color=INK)
    label(ax, 50, 7.0, "artifacts, not log lines — every one has an identity that can be cited later",
          fs=7.4, italic=True)
    arrow(ax, (cs[-1], 36.0), (cs[0], 36.0), color=RED, lw=1.6, rad=0.10, ms=10)
    return save(fig, 13, "Analytics Development Pipeline")


def fig14():
    fig, ax = canvas(10, 5.0, 100, 50)
    cols = [("RAW DATA", ["dataset raw", "validation report"], BLUE),
            ("DERIVED DATA", ["dataset clean", "feature_set"], GREEN),
            ("EXPERIMENTS", ["code_rev", "environment", "run"], VIOLET),
            ("MODELS", ["model", "evaluation"], AMBER),
            ("OPERATIONS", ["deployment", "prediction_batch", "drift_report"], ORANGE)]
    fillmap = {BLUE: BLUE_F, GREEN: GREEN_F, VIOLET: VIOLET_F, AMBER: AMBER_F, ORANGE: ORANGE_F}
    n = len(cols); w = (94 - (n - 1) * 2.2) / n
    for i, (title, items, col) in enumerate(cols):
        x = 3 + i * (w + 2.2)
        ax.add_patch(FancyBboxPatch((x, 8), w, 33, boxstyle="round,pad=0,rounding_size=0.02",
                     linewidth=1.3, edgecolor=col, facecolor="#fcfdfe", zorder=1))
        label(ax, x + w / 2, 38.4, title, fs=7.6, color=col, bold=True)
        for j, it in enumerate(items):
            box(ax, x + 1.2, 31.5 - j * 8.0, w - 2.4, 6.6, it, fill=fillmap[col],
                edge=col, fs=7.2, lw=1.0)
        if i < n - 1:
            arrow(ax, (x + w + 0.3, 24), (x + w + 1.9, 24), color=MUTED, lw=1.4, ms=9)
    label(ax, 50, 45.5, "backward traversal answers 'what produced this?'   ·   forward traversal answers 'what did this affect?'",
          fs=8.0, color=INK, bold=True)
    arrow(ax, (92, 4.5), (8, 4.5), color=RED, lw=1.6, ms=10)
    label(ax, 50, 2.2, "TRIGGERS_RETRAIN closes the loop from drift back to raw data", fs=7.2, color=RED, bold=True)
    return save(fig, 14, "End-to-End Digital Thread Traceability Model")


def fig15():
    fig, ax = canvas(10, 4.8, 100, 48)
    band(ax, 3, 37, 94, 8.5, "SCHEDULER   ·   Prefect flow or Airflow DAG",
         "cron or event trigger · dependency resolution · retry policy · run context propagation",
         fill=GREY_F, edge=GREY, title_color=INK, fs=8.8, body_fs=7.0)
    tasks = ["ingest", "clean", "features", "train", "promote", "serve", "monitor"]
    n = len(tasks); w = (94 - (n - 1) * 2.0) / n
    cs = []
    for i, t in enumerate(tasks):
        x = 3 + i * (w + 2.0)
        box(ax, x, 20, w, 9.0, t, fill=VIOLET_F, edge=VIOLET, fs=8.2, bold=True)
        cs.append(x + w / 2)
        arrow(ax, (x + w / 2, 36.7), (x + w / 2, 29.3), color=GREY, lw=1.0, ls=(0, (2, 2)), ms=7)
        if i < n - 1:
            arrow(ax, (x + w + 0.3, 24.5), (x + w + 1.7, 24.5), color=VIOLET, lw=1.3, ms=9)
    for cx in cs:
        arrow(ax, (cx, 19.7), (cx, 14.3), color=AMBER, lw=1.0, ls=(0, (3, 2)), ms=7)
    band(ax, 3, 4.0, 94, 10.0, "LEDGER TRANSACTION PER TASK",
         "open run → attach inputs → attach outputs → write outcome node with status and duration;\n"
         "a task that fails still leaves a failure outcome, so the gap in the thread is itself recorded",
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=8.8, body_fs=6.9)
    return save(fig, 15, "Workflow Orchestration Framework")


def fig16():
    fig, ax = canvas(10, 4.8, 100, 48)
    ax.add_patch(FancyBboxPatch((3, 26), 44, 18, boxstyle="round,pad=0,rounding_size=0.02",
                 linewidth=1.5, edgecolor=TEAL, facecolor=TEAL_F, zorder=1))
    label(ax, 25, 41.3, "DataOps", fs=10.0, color=TEAL, bold=True)
    for i, t in enumerate(["ingest & validate", "transform & profile", "version & publish"]):
        box(ax, 6, 36.0 - i * 4.4, 38, 3.8, t, fill="white", edge=TEAL, fs=7.4, lw=1.0)
    ax.add_patch(FancyBboxPatch((53, 26), 44, 18, boxstyle="round,pad=0,rounding_size=0.02",
                 linewidth=1.5, edgecolor=VIOLET, facecolor=VIOLET_F, zorder=1))
    label(ax, 75, 41.3, "MLOps", fs=10.0, color=VIOLET, bold=True)
    for i, t in enumerate(["train & track", "evaluate & promote", "deploy & monitor"]):
        box(ax, 56, 36.0 - i * 4.4, 38, 3.8, t, fill="white", edge=VIOLET, fs=7.4, lw=1.0)
    arrow(ax, (47.3, 35), (52.7, 35), color=MUTED, lw=1.6, ms=10, style="<|-|>")
    label(ax, 50, 46.0, "two operating disciplines, one record", fs=8.6, bold=True, color=INK)
    band(ax, 3, 11, 94, 11.5, "THREAD LEDGER   ·   the shared substrate",
         "DataOps writes dataset, validation and feature_set nodes; MLOps writes run, model, deployment and drift nodes.\n"
         "Because both use the same vocabulary, a question can cross the boundary in a single traversal.",
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=9.0, body_fs=6.9)
    for x in (25, 75):
        arrow(ax, (x, 25.7), (x, 22.8), color=AMBER, lw=1.3, ms=9)
    label(ax, 50, 6.0, "the integration point is the vocabulary, not a shared tool or a shared team",
          fs=7.6, italic=True)
    return save(fig, 16, "DataOps-MLOps Integration Model")


def fig17():
    fig, ax = canvas(10, 5.0, 100, 50)
    pillars = [("Transparency", ["feature definitions\nstored, not inferred",
                                 "prediction carries\nmodel digest"], GREEN),
               ("Accountability", ["append-only history",
                                   "promotion gate\nrecorded with reason"], VIOLET),
               ("Auditability", ["validation verdicts\nas first-class nodes",
                                 "evidence exportable\nas JSON or HTML"], AMBER),
               ("Compliance", ["data origin recorded\n(real or replica)",
                               "retention via\nimmutable ledger"], RED)]
    fillmap = {GREEN: GREEN_F, VIOLET: VIOLET_F, AMBER: AMBER_F, RED: RED_F}
    n = len(pillars); w = (94 - (n - 1) * 2.4) / n
    for i, (t, items, col) in enumerate(pillars):
        x = 3 + i * (w + 2.4)
        box(ax, x, 36, w, 7.5, t, fill=fillmap[col], edge=col, fs=9.0, bold=True)
        for j, it in enumerate(items):
            box(ax, x, 24.5 - j * 10.0, w, 8.5, it, fill="white", edge=col, fs=7.2, lw=1.0)
            arrow(ax, (x + w / 2, (36 if j == 0 else 24.5 - (j - 1) * 10.0) - 0.3),
                  (x + w / 2, 24.5 - j * 10.0 + 8.8), color=col, lw=0.9, ms=7)
    band(ax, 3, 2.5, 94, 7.5, "AUDIT QUESTION ANSWERED IN ONE TRAVERSAL",
         "\"show every artifact that contributed to this prediction, the checks its data passed, and who promoted the model\"",
         fill="#f7f9fb", edge=LINE, title_color=INK, fs=8.4, body_fs=7.2)
    label(ax, 50, 47.0, "Governance and explainability are properties of the record, not a separate reporting step",
          fs=8.0, bold=True, color=INK)
    return save(fig, 17, "Governance and Explainability Framework")


def fig18():
    fig, ax = canvas(9.6, 5.0, 100, 50)
    rings = [("DATA", 20.5, BLUE_F, BLUE), ("INFORMATION", 16.0, GREEN_F, GREEN),
             ("INSIGHT", 11.5, VIOLET_F, VIOLET), ("DECISION", 7.0, AMBER_F, AMBER)]
    cx, cy = 32, 25
    for t, r, fillc, col in rings:
        ax.add_patch(Circle((cx, cy), r, facecolor=fillc, edgecolor=col, lw=1.6, zorder=2))
    for t, r, fillc, col in rings:
        ax.text(cx, cy + r - 2.3, t, ha="center", va="center", fontsize=7.4,
                color=col, fontweight="bold", zorder=6)
    items = [("sensor readings, batch files", BLUE), ("validated, versioned datasets", GREEN),
             ("calibrated failure probability", VIOLET), ("schedule maintenance or not", AMBER)]
    for i, (t, col) in enumerate(items):
        y = 42 - i * 9.5
        box(ax, 58, y - 3.4, 39, 6.8, t, fill="white", edge=col, fs=7.6, lw=1.2)
        arrow(ax, (cx + rings[i][1] - 1.0, cy + (10 - i * 7)), (57.5, y), color=col,
              lw=1.0, ls=(0, (3, 2)), ms=8, rad=0.08)
    label(ax, 50, 47.5, "each step up is only trustworthy if the step below it is traceable",
          fs=8.0, bold=True, color=INK)
    return save(fig, 18, "Decision Intelligence Framework")


def fig19():
    fig, ax = canvas(10, 4.2, 100, 42)
    steps = [("Reading", "one machine\nobservation"), ("Features", "derived on the\nserving path"),
             ("Model", "promoted\ndeployment"), ("Probability", "calibrated\nfailure score"),
             ("Threshold", "operating point\nand cost ratio"), ("Action", "inspect, schedule,\nor ignore")]
    centers, w = chain(ax, steps, y=20, h=12.5, left=3, right=97, gap=2.5, fs=8.2,
                       pair=(ORANGE, ORANGE_F), numbered=True)
    for cx in centers:
        arrow(ax, (cx, 19.7), (cx, 13.3), color=AMBER, lw=1.0, ls=(0, (3, 2)), ms=7)
    band(ax, 3, 3.5, 94, 9.5, "LINEAGE TRAVELS WITH THE ANSWER",
         "the API response carries the deployment version, the model digest and the deployment node id, so the decision can be re-opened later",
         fill=AMBER_F, edge=AMBER, title_color="#6b4a12", fs=8.8, body_fs=7.0)
    label(ax, 50, 38.5, "an operator acting on a prediction can reach its full provenance in one further call",
          fs=7.8, italic=True)
    return save(fig, 19, "Analytics-to-Decision Pipeline")


def fig20():
    fig, ax = canvas(10, 4.2, 100, 42)
    band(ax, 3, 30, 94, 10.5, "EXPERIMENTAL TESTBED",
         "Linux x86-64 · Intel Xeon 2.80 GHz, 2 vCPU, 7 GiB RAM · Python 3.13 · pandas 3.0 · scikit-learn 1.9 · SQLite (stdlib)\n"
         "both arms receive identical input data and the same random seed; only the presence of the thread differs",
         fill=GREY_F, edge=GREY, title_color=INK, fs=9.0, body_fs=6.9)
    arms = [("TREATMENT\nthreaded pipeline", ["7 stages", "ledger instrumented",
                                              "32 nodes / 50 edges"], GREEN),
            ("CONTROL\nbaseline script", ["same models", "no lineage recorded",
                                          "single script"], GREY)]
    for i, (t, items, col) in enumerate(arms):
        x = 6 + i * 46
        fillc = GREEN_F if col == GREEN else GREY_F
        box(ax, x, 18, 42, 8.5, t, fill=fillc, edge=col, fs=8.6, bold=True)
        for j, it in enumerate(items):
            box(ax, x + 2, 13.0 - j * 4.4, 38, 3.8, it, fill="white", edge=col, fs=7.2, lw=1.0)
        arrow(ax, (x + 21, 29.7), (x + 21, 26.8), color=GREY, lw=1.2, ms=8)
    return save(fig, 20, "Experimental Testbed Architecture")


def fig21():
    fig, ax = canvas(10, 4.6, 100, 46)
    groups = [("TRACEABILITY", ["lineage completeness", "time to trace", "nodes reached"], AMBER),
              ("REPRODUCIBILITY", ["identity match rate", "run-to-run variance"], GREEN),
              ("EFFICIENCY", ["instrumentation cost", "fingerprinting cost", "end-to-end overhead"], VIOLET),
              ("PREDICTIVE QUALITY", ["PR-AUC", "ROC-AUC", "precision / recall"], BLUE),
              ("OPERATIONAL", ["drift detection latency", "ledger footprint"], ORANGE)]
    fillmap = {AMBER: AMBER_F, GREEN: GREEN_F, VIOLET: VIOLET_F, BLUE: BLUE_F, ORANGE: ORANGE_F}
    n = len(groups); w = (94 - (n - 1) * 2.0) / n
    for i, (t, items, col) in enumerate(groups):
        x = 3 + i * (w + 2.0)
        box(ax, x, 30, w, 7.5, t, fill=fillmap[col], edge=col, fs=7.8, bold=True)
        for j, it in enumerate(items):
            box(ax, x, 23.5 - j * 6.2, w, 5.2, it, fill="white", edge=col, fs=6.8, lw=1.0)
    label(ax, 50, 42.0, "every metric is computed by code in the repository, not reported by hand",
          fs=8.2, bold=True, color=INK)
    band(ax, 3, 2.0, 94, 5.0, "", None, fill="#f7f9fb", edge=LINE)
    label(ax, 50, 4.5, "experiments/evaluate_framework.py  ·  reproducible with  python run.py evaluate",
          fs=7.4, color=INK)
    return save(fig, 21, "Evaluation Framework")


if __name__ == "__main__":
    for f in (fig11, fig12, fig13, fig14, fig15, fig16, fig17, fig18, fig19, fig20, fig21):
        f()
