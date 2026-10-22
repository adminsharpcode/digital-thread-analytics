/* Digital Thread Analytics — dashboard.
 *
 * Every panel is populated from the backend at load time; nothing is baked in.
 * The lineage explorer is the point of the page: pick an artifact, walk the
 * thread in either direction, and see how long the answer took.
 */

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return body;
}

const fmt = {
  pct: (v) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(2)} %`),
  num: (v, d = 3) => (v === null || v === undefined ? "—" : Number(v).toFixed(d)),
  int: (v) => (v === null || v === undefined ? "—" : Number(v).toLocaleString()),
};

// ---------------------------------------------------------------- bootstrap
let STATE = { nodes: [], overview: null };

async function boot() {
  let health;
  try {
    health = await api("/api/health");
  } catch (err) {
    setHealth("backend unreachable", "pill-bad");
    return;
  }

  if (health.status !== "ok") {
    setHealth(health.status, "pill-bad");
    $("#empty").classList.remove("hidden");
    return;
  }

  setHealth(`${health.model} · ${health.deployment}`, "pill-ok");
  $("#app").classList.remove("hidden");

  // everything else can load in parallel
  await Promise.all([
    loadOverview(),
    loadModels(),
    loadDrift(),
    loadNodes(),
  ]).catch((err) => showError($("#app"), err.message));
}

function setHealth(text, cls) {
  const n = $("#health");
  n.textContent = text;
  n.className = `pill ${cls}`;
}

function showError(parent, message) {
  const n = el("div", "err", message);
  parent.prepend(n);
}

// ----------------------------------------------------------------- overview
async function loadOverview() {
  const o = await api("/api/overview");
  STATE.overview = o;

  const tiles = $("#tiles");
  tiles.innerHTML = "";

  const add = (k, v, n, cls) => {
    const t = el("div", `tile ${cls || ""}`);
    t.append(el("div", "k", k), el("div", "v", v));
    if (n) t.append(el("div", "n", n));
    tiles.append(t);
  };

  const dep = o.deployment;
  add("Deployment", dep ? dep.version : "none",
      dep ? `${dep.attrs.model} · ${dep.attrs.primary_metric} ${fmt.num(dep.attrs.score, 3)}` : "");

  const ds = o.dataset;
  const rows = ds.clean ? ds.clean.attrs.rows : null;
  add("Dataset", fmt.int(rows) + " rows",
      `${fmt.pct(ds.positive_rate)} positive · origin: ${ds.origin || "unknown"}`,
      ds.origin === "synthetic" ? "is-warn" : "");

  const f = o.feature_set;
  add("Features", f ? f.attrs.n_features : "—",
      f ? `feature set ${f.version}` : "");

  if (o.drift) {
    add("Drift (PSI)", fmt.num(o.drift.psi, 2),
        `${o.drift.worst_feature} · threshold ${o.drift.threshold}`,
        o.drift.drifted ? "is-warn" : "is-ok");
  } else {
    add("Drift", "—", "no report yet");
  }

  const counts = $("#ledger-counts");
  counts.innerHTML = "";
  const total = el("span", "chip");
  total.innerHTML = `<b>${o.ledger.n_nodes}</b> nodes · <b>${o.ledger.n_edges}</b> edges`;
  counts.append(total);
  Object.entries(o.ledger.nodes)
    .sort((a, b) => b[1] - a[1])
    .forEach(([type, n]) => {
      const c = el("span", "chip");
      c.innerHTML = `${type} · <b>${n}</b>`;
      counts.append(c);
    });

  if (ds.origin === "synthetic") {
    $("#foot-note").textContent =
      "This run used a specification replica of AI4I 2020, not the UCI file — " +
      "the ledger records that on the dataset node.";
  } else {
    $("#foot-note").textContent = "Digital Thread Analytics · AI4I 2020";
  }
}

// ------------------------------------------------------------------- models
async function loadModels() {
  const data = await api("/api/models");
  $("#models-note").textContent =
    `Ranked on ${data.primary_metric}; promotion gate at ${data.gate}.`;

  const cols = [
    ["Model", (m) => m.name, false],
    ["PR-AUC", (m) => fmt.num(m.metrics.average_precision), true],
    ["ROC-AUC", (m) => fmt.num(m.metrics.roc_auc), true],
    ["F1", (m) => fmt.num(m.metrics.f1), true],
    ["Prec.", (m) => fmt.num(m.metrics.precision), true],
    ["Recall", (m) => fmt.num(m.metrics.recall), true],
  ];

  const t = $("#models-table");
  t.innerHTML = "";
  const head = el("tr");
  cols.forEach(([label, , num]) => {
    head.append(el("th", num ? "num" : null, label));
  });
  const thead = el("thead");
  thead.append(head);
  t.append(thead);

  const body = el("tbody");
  data.models.forEach((m) => {
    const tr = el("tr", m.promoted ? "is-promoted" : null);
    cols.forEach(([, get, num], i) => {
      const td = el("td", num ? "num" : null, get(m));
      if (i === 0 && m.promoted) td.append(el("span", "badge", "promoted"));
      tr.append(td);
    });
    body.append(tr);
  });
  t.append(body);
}

// -------------------------------------------------------------------- drift
async function loadDrift() {
  let d;
  try {
    d = await api("/api/drift");
  } catch {
    $("#drift-note").textContent = "No drift report in the ledger yet.";
    return;
  }

  const sim = d.simulation || {};
  $("#drift-note").textContent =
    `Population Stability Index per feature, threshold ${d.threshold}. ` +
    (d.simulated
      ? `The monitored batch is a simulated shift: +${sim.tool_wear_offset_min} min tool wear, torque ×${sim.torque_scale}.`
      : "");

  const wrap = $("#drift-bars");
  wrap.innerHTML = "";
  const max = Math.max(...d.per_feature.map((r) => r.psi), d.threshold * 1.5);

  d.per_feature.forEach((r) => {
    const over = r.psi >= d.threshold;
    const row = el("div", "bar-row");
    row.append(el("div", "name", r.feature));

    const track = el("div", "bar-track");
    const fill = el("i", `bar-fill ${over ? "over" : ""}`);
    fill.style.width = `${Math.max(1.5, (r.psi / max) * 100)}%`;
    fill.style.display = "block";
    track.append(fill);
    row.append(track);

    row.append(el("div", `val ${over ? "over" : ""}`, r.psi.toFixed(3)));
    wrap.append(row);
  });
}

// ---------------------------------------------------------------- explorer
async function loadNodes() {
  const data = await api("/api/nodes");
  STATE.nodes = data.nodes;

  const types = [...new Set(data.nodes.map((n) => n.type))].sort();
  const typeSel = $("#node-type");
  typeSel.innerHTML = "";
  types.forEach((t) => {
    const o = el("option", null, t);
    o.value = t;
    typeSel.append(o);
  });
  typeSel.value = types.includes("model") ? "model" : types[0];

  typeSel.addEventListener("change", fillNodeSelect);
  $("#node-id").addEventListener("change", runExplorer);
  document.querySelectorAll(".seg-btn").forEach((b) => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".seg-btn").forEach((x) => x.classList.remove("is-active"));
      b.classList.add("is-active");
      runExplorer();
    });
  });

  fillNodeSelect();
}

// Two explorer queries can be in flight at once (changing the type also
// changes the selected artifact). A token makes the most recent request the
// only one allowed to render, so a slow earlier reply cannot append to the
// container a later one has already filled.
let EXPLORER_TOKEN = 0;

function fillNodeSelect(skipRun) {
  const type = $("#node-type").value;
  const sel = $("#node-id");
  sel.innerHTML = "";
  STATE.nodes
    .filter((n) => n.type === type)
    .forEach((n) => {
      const o = el("option", null, n.version ? `${n.name} @ ${n.version}` : n.name);
      o.value = n.id;
      sel.append(o);
    });
  if (!skipRun) runExplorer();
}

function currentDirection() {
  return document.querySelector(".seg-btn.is-active").dataset.dir;
}

async function runExplorer() {
  const id = $("#node-id").value;
  if (!id) return;
  const token = ++EXPLORER_TOKEN;
  const dir = currentDirection();
  const meta = $("#trace-meta");
  const out = $("#trace-result");
  out.innerHTML = "";
  meta.textContent = "querying the ledger…";

  try {
    if (dir === "trace") {
      const r = await api(`/api/trace/${id}`);
      if (token !== EXPLORER_TOKEN) return;
      out.innerHTML = "";
      meta.innerHTML =
        `<b>${r.nodes_reached}</b> upstream artifacts reached in ` +
        `<b>${r.elapsed_ms.toFixed(2)} ms</b> — everything <code>${r.node.label}</code> depended on.`;
      renderChain(out, r.provenance);
    } else {
      const r = await api(`/api/impact/${id}`);
      if (token !== EXPLORER_TOKEN) return;
      out.innerHTML = "";
      meta.innerHTML =
        `<b>${r.count}</b> downstream artifacts reached in ` +
        `<b>${r.elapsed_ms.toFixed(2)} ms</b> — everything this artifact went on to affect.`;
      renderChain(out, r.affected);
    }
  } catch (err) {
    if (token !== EXPLORER_TOKEN) return;
    meta.textContent = "";
    out.append(el("div", "err", err.message));
  }
}

const INTERESTING = [
  "rows", "columns", "n_features", "algorithm", "average_precision", "roc_auc",
  "passed", "checks", "psi", "threshold", "status", "seconds", "score",
  "positive_rate", "origin", "flagged", "model",
];

function renderChain(parent, rows) {
  if (!rows.length) {
    parent.append(el("p", "muted", "Nothing in that direction — this is an endpoint of the thread."));
    return;
  }
  rows.forEach((r) => {
    const step = el("div", "step");

    const rail = el("div", "rail");
    rail.append(el("div", "dot"), el("div", "line"));
    step.append(rail);

    const node = el("div", `node t-${r.type}`);
    const head = el("div", "head");
    head.append(el("span", "type", r.type));
    head.append(el("span", "label", r.label));
    head.append(el("span", "via", r.via));
    head.append(el("span", "type", `depth ${r.depth}`));
    node.append(head);

    if (r.attrs) {
      const bits = INTERESTING
        .filter((k) => r.attrs[k] !== undefined && r.attrs[k] !== null)
        .map((k) => `${k}: ${r.attrs[k]}`);
      if (bits.length) node.append(el("div", "attrs", bits.join("  ·  ")));
    }

    step.append(node);
    parent.append(step);
  });
}

// ------------------------------------------------------------------ predict
$("#predict-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const btn = ev.target.querySelector("button[type=submit]");
  btn.disabled = true;
  btn.textContent = "Scoring…";

  const payload = {};
  new FormData(ev.target).forEach((v, k) => {
    payload[k] = k === "type" ? v : Number(v);
  });

  const box = $("#predict-result");
  box.classList.remove("hidden");
  box.innerHTML = "";

  try {
    const r = await api("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const verdict = el("div", "verdict");
    verdict.append(el("span", "p", fmt.pct(r.failure_probability)));
    verdict.append(el("span", `tag ${r.prediction ? "tag-fail" : "tag-pass"}`,
      r.prediction ? "failure predicted" : "no failure predicted"));
    verdict.append(el("span", "muted small", `scored in ${r.elapsed_ms.toFixed(1)} ms`));
    box.append(verdict);

    const meter = el("div", "meter");
    const bar = el("i");
    bar.style.width = `${Math.min(100, r.failure_probability * 100)}%`;
    if (r.prediction) bar.style.background = "var(--warn)";
    meter.append(bar);
    box.append(meter);

    const dl = el("dl", "kv");
    const pair = (k, v) => { dl.append(el("dt", null, k), el("dd", null, v)); };
    Object.entries(r.derived_features).forEach(([k, v]) => pair(k, v));
    pair("deployment", r.lineage.deployment);
    pair("model", r.lineage.model);
    pair("model digest", r.lineage.model_digest);
    box.append(dl);

    const linkRow = el("div");
    const link = el("button", "linkish", "Trace this prediction back to raw data →");
    link.addEventListener("click", () => {
      $("#node-type").value = "deployment";
      fillNodeSelect(true);
      $("#node-id").value = r.lineage.deployment_node;
      document.querySelectorAll(".seg-btn").forEach((x) =>
        x.classList.toggle("is-active", x.dataset.dir === "trace"));
      runExplorer();
      $("#trace-meta").scrollIntoView({ behavior: "smooth", block: "center" });
    });
    linkRow.append(link);
    box.append(linkRow);

  } catch (err) {
    box.append(el("div", "err", err.message));
  } finally {
    btn.disabled = false;
    btn.textContent = "Predict";
  }
});

$("#btn-worn").addEventListener("click", () => {
  // a plausible overstrain case: heavy wear and high torque
  const set = (name, value) => { $(`[name="${name}"]`).value = value; };
  set("air_temp_K", 302.4);
  set("process_temp_K", 310.9);
  set("rot_speed_rpm", 1320);
  set("torque_Nm", 64.5);
  set("tool_wear_min", 215);
  set("type", "L");
});

boot();
