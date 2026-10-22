"""Thread Ledger — an append-only lineage graph for the data science lifecycle.

The ledger is the contribution of this project. Every stage of the pipeline
writes nodes and typed edges into it, so that the whole lifecycle — raw data,
validation outcomes, features, runs, models, deployments, predictions and drift
reports — becomes one graph that can be traversed in either direction.

Design decisions worth defending in the report:

1. Content-addressed node identity. A node's id is a digest of its type, name,
   version and content digest. Re-running an unchanged stage therefore produces
   the *same* node id rather than a duplicate, which is what makes the
   reproducibility check in experiments/evaluate_framework.py meaningful.
2. Append-only enforced at the storage layer. SQLite triggers reject UPDATE and
   DELETE on nodes and edges. Lineage that can be quietly rewritten is not
   evidence.
3. Tool-agnostic. The ledger records MLflow run ids, DVC hashes and file paths
   as plain attributes. It does not depend on any of those tools being present.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, Sequence

# --------------------------------------------------------------------------
# vocabulary
# --------------------------------------------------------------------------

NODE_TYPES = (
    "dataset",
    "validation",
    "feature_set",
    "code_rev",
    "environment",
    "run",
    "model",
    "evaluation",
    "deployment",
    "prediction_batch",
    "drift_report",
)

# Every edge points backwards in time, from an artifact to what it depended
# on, following the W3C PROV convention (wasDerivedFrom, wasGeneratedBy, used).
# One direction for every relation is what makes a single traversal function
# correct for the whole graph.
EDGE_TYPES = (
    "DERIVED_FROM",      # derived dataset / feature_set -> its source
    "VALIDATES",         # validation report -> the dataset it checked
    "TRAINED_ON",        # run -> feature_set
    "BUILT_FROM",        # run -> code_rev
    "RAN_IN",            # run -> environment
    "PRODUCED_BY",       # model / evaluation / dataset -> the run that made it
    "EVALUATES",         # evaluation -> the model it scored
    "PROMOTED_FROM",     # deployment -> the model it serves
    "SERVED_BY",         # prediction_batch -> deployment
    "OBSERVED_ON",       # drift_report -> prediction_batch
    "TRIGGERS_RETRAIN",  # drift_report -> the dataset it sends back for retraining
)

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS nodes (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    version     TEXT,
    digest      TEXT,
    attrs       TEXT NOT NULL DEFAULT '{}',
    run_id      TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    id          TEXT PRIMARY KEY,
    src         TEXT NOT NULL REFERENCES nodes(id),
    dst         TEXT NOT NULL REFERENCES nodes(id),
    rel         TEXT NOT NULL,
    attrs       TEXT NOT NULL DEFAULT '{}',
    run_id      TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE (src, dst, rel)
);

CREATE INDEX IF NOT EXISTS ix_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS ix_nodes_name ON nodes(name);
CREATE INDEX IF NOT EXISTS ix_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS ix_edges_dst ON edges(dst);

-- append-only: history is evidence, so it must not be rewritable
CREATE TRIGGER IF NOT EXISTS nodes_no_update
BEFORE UPDATE ON nodes
BEGIN SELECT RAISE(ABORT, 'thread ledger is append-only: nodes cannot be updated'); END;

CREATE TRIGGER IF NOT EXISTS nodes_no_delete
BEFORE DELETE ON nodes
BEGIN SELECT RAISE(ABORT, 'thread ledger is append-only: nodes cannot be deleted'); END;

CREATE TRIGGER IF NOT EXISTS edges_no_update
BEFORE UPDATE ON edges
BEGIN SELECT RAISE(ABORT, 'thread ledger is append-only: edges cannot be updated'); END;

CREATE TRIGGER IF NOT EXISTS edges_no_delete
BEFORE DELETE ON edges
BEGIN SELECT RAISE(ABORT, 'thread ledger is append-only: edges cannot be deleted'); END;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def node_id(node_type: str, name: str, version: str | None,
            digest: str | None) -> str:
    """Content-addressed identity: same inputs -> same id, always."""
    key = "|".join([node_type, name, version or "", digest or ""])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    name: str
    version: str | None
    digest: str | None
    attrs: dict[str, Any]
    run_id: str | None
    created_at: str

    @property
    def label(self) -> str:
        return f"{self.type}:{self.name}" + (f"@{self.version}" if self.version else "")


@dataclass(frozen=True)
class Edge:
    id: str
    src: str
    dst: str
    rel: str
    attrs: dict[str, Any]
    run_id: str | None
    created_at: str


@dataclass
class RunHandle:
    """Handle passed to a stage so it can attach everything it touches."""
    ledger: "ThreadLedger"
    run_node_id: str
    stage: str
    started: float = field(default_factory=time.perf_counter)

    # -- convenience wrappers that automatically stamp the run id ----------
    def node(self, node_type: str, name: str, *, version: str | None = None,
             digest: str | None = None, **attrs: Any) -> str:
        return self.ledger.add_node(node_type, name, version=version,
                                    digest=digest, run_id=self.run_node_id,
                                    **attrs)

    def edge(self, src: str, dst: str, rel: str, **attrs: Any) -> str:
        return self.ledger.add_edge(src, dst, rel, run_id=self.run_node_id,
                                    **attrs)

    def used(self, node: str, rel: str = "TRAINED_ON") -> str:
        """The run depended on `node` — edge points from the run to it."""
        return self.edge(self.run_node_id, node, rel)

    def produced(self, node: str) -> str:
        """`node` came out of this run — edge points from it back to the run."""
        return self.edge(node, self.run_node_id, "PRODUCED_BY")


class LedgerError(RuntimeError):
    pass


class ThreadLedger:
    """SQLite-backed append-only lineage graph."""

    def __init__(self, path: str | os.PathLike[str] = "artifacts/thread_ledger.db"):
        self.path = str(path)
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        # instrumentation for the overhead experiment: how many writes the
        # thread cost, and how much wall clock those writes consumed
        self.write_count = 0
        self.write_seconds = 0.0

    # ------------------------------------------------------------------ io
    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ThreadLedger":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --------------------------------------------------------------- write
    def add_node(self, node_type: str, name: str, *, version: str | None = None,
                 digest: str | None = None, run_id: str | None = None,
                 **attrs: Any) -> str:
        if node_type not in NODE_TYPES:
            raise LedgerError(f"unknown node type {node_type!r}; "
                              f"expected one of {NODE_TYPES}")
        t0 = time.perf_counter()
        nid = node_id(node_type, name, version, digest)
        row = self._conn.execute("SELECT id FROM nodes WHERE id = ?", (nid,)).fetchone()
        if row is not None:
            # identical content already recorded — idempotent by design
            self.write_seconds += time.perf_counter() - t0
            return nid
        self._conn.execute(
            "INSERT INTO nodes (id, type, name, version, digest, attrs, run_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (nid, node_type, name, version, digest,
             json.dumps(attrs, default=str, sort_keys=True), run_id, _now()),
        )
        self._conn.commit()
        self.write_count += 1
        self.write_seconds += time.perf_counter() - t0
        return nid

    def add_edge(self, src: str, dst: str, rel: str, *,
                 run_id: str | None = None, **attrs: Any) -> str:
        if rel not in EDGE_TYPES:
            raise LedgerError(f"unknown edge type {rel!r}; expected one of {EDGE_TYPES}")
        t0 = time.perf_counter()
        for end, which in ((src, "src"), (dst, "dst")):
            if self._conn.execute("SELECT 1 FROM nodes WHERE id = ?", (end,)).fetchone() is None:
                raise LedgerError(f"{which} node {end!r} is not in the ledger")
        existing = self._conn.execute(
            "SELECT id FROM edges WHERE src = ? AND dst = ? AND rel = ?",
            (src, dst, rel)).fetchone()
        if existing is not None:
            self.write_seconds += time.perf_counter() - t0
            return str(existing["id"])
        eid = uuid.uuid4().hex[:16]
        self._conn.execute(
            "INSERT INTO edges (id, src, dst, rel, attrs, run_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (eid, src, dst, rel,
             json.dumps(attrs, default=str, sort_keys=True), run_id, _now()),
        )
        self._conn.commit()
        self.write_count += 1
        self.write_seconds += time.perf_counter() - t0
        return eid

    # ----------------------------------------------------------- run scope
    @contextmanager
    def run(self, stage: str, *, code_rev: str | None = None,
            environment: str | None = None, **params: Any) -> Iterator[RunHandle]:
        """Open a stage as a ledger transaction.

        Records a `run` node, links it to the code revision and environment,
        and on exit stamps status and wall-clock duration onto a terminal
        attribute node so the timing itself is part of the thread.
        """
        started_wall = time.perf_counter()
        run_key = f"{stage}-{uuid.uuid4().hex[:8]}"
        # no "status" attribute here: the ledger is append-only, so a run's
        # outcome is recorded as its own node when the stage finishes rather
        # than by mutating this one
        rid = self.add_node("run", stage, version=run_key,
                            digest=run_key, **params)
        handle = RunHandle(ledger=self, run_node_id=rid, stage=stage)

        if code_rev:
            cid = self.add_node("code_rev", "repository", version=code_rev,
                                digest=code_rev)
            self.add_edge(rid, cid, "BUILT_FROM", run_id=rid)
        if environment:
            eid = self.add_node("environment", "python-env", version=environment[:12],
                                digest=environment)
            self.add_edge(rid, eid, "RAN_IN", run_id=rid)

        status = "succeeded"
        try:
            yield handle
        except Exception as exc:                      # noqa: BLE001
            status = f"failed: {type(exc).__name__}"
            raise
        finally:
            elapsed = time.perf_counter() - started_wall
            # append-only, so the outcome is a new node linked to the run
            oid = self.add_node("evaluation", f"{stage}-outcome",
                                version=run_key, digest=f"{run_key}-outcome",
                                status=status, seconds=round(elapsed, 4))
            self.add_edge(oid, rid, "PRODUCED_BY", run_id=rid)

    # ---------------------------------------------------------------- read
    def get_node(self, nid: str) -> Node | None:
        row = self._conn.execute("SELECT * FROM nodes WHERE id = ?", (nid,)).fetchone()
        return self._row_to_node(row) if row else None

    def find(self, *, node_type: str | None = None, name: str | None = None,
             version: str | None = None) -> list[Node]:
        clauses, args = [], []
        if node_type:
            clauses.append("type = ?"); args.append(node_type)
        if name:
            clauses.append("name = ?"); args.append(name)
        if version:
            clauses.append("version = ?"); args.append(version)
        sql = "SELECT * FROM nodes"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at"
        return [self._row_to_node(r) for r in self._conn.execute(sql, args)]

    def latest(self, node_type: str, name: str | None = None) -> Node | None:
        found = self.find(node_type=node_type, name=name)
        return found[-1] if found else None

    def edges_of(self, nid: str, direction: str = "out") -> list[Edge]:
        col = "src" if direction == "out" else "dst"
        rows = self._conn.execute(
            f"SELECT * FROM edges WHERE {col} = ? ORDER BY created_at", (nid,))
        return [self._row_to_edge(r) for r in rows]

    # ----------------------------------------------------------- traversal
    def _walk(self, nid: str, direction: str, max_depth: int | None,
              rels: Sequence[str] | None) -> list[tuple[Node, str, int]]:
        seen: set[str] = {nid}
        out: list[tuple[Node, str, int]] = []
        frontier = [(nid, 0)]
        while frontier:
            cur, depth = frontier.pop(0)
            if max_depth is not None and depth >= max_depth:
                continue
            # edges point towards dependencies, so "upstream" follows them
            # outward and "downstream" follows them in reverse
            for e in self.edges_of(cur, "out" if direction == "upstream" else "in"):
                if rels and e.rel not in rels:
                    continue
                nxt = e.dst if direction == "upstream" else e.src
                if nxt in seen:
                    continue
                seen.add(nxt)
                node = self.get_node(nxt)
                if node is None:
                    continue
                out.append((node, e.rel, depth + 1))
                frontier.append((nxt, depth + 1))
        return out

    def upstream(self, nid: str, max_depth: int | None = None,
                 rels: Sequence[str] | None = None) -> list[tuple[Node, str, int]]:
        """Everything this node depends on. Answers 'where did this come from?'"""
        return self._walk(nid, "upstream", max_depth, rels)

    def downstream(self, nid: str, max_depth: int | None = None,
                   rels: Sequence[str] | None = None) -> list[tuple[Node, str, int]]:
        """Everything affected by this node. Answers 'what does this touch?'"""
        return self._walk(nid, "downstream", max_depth, rels)

    def trace(self, nid: str) -> dict[str, Any]:
        """Full provenance bundle for one node, grouped by node type."""
        node = self.get_node(nid)
        if node is None:
            raise LedgerError(f"node {nid!r} not in ledger")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for n, rel, depth in self.upstream(nid):
            grouped.setdefault(n.type, []).append(
                {"id": n.id, "label": n.label, "via": rel, "depth": depth,
                 "attrs": n.attrs})
        return {"node": {"id": node.id, "label": node.label, "attrs": node.attrs},
                "provenance": grouped,
                "nodes_reached": sum(len(v) for v in grouped.values())}

    # --------------------------------------------------------------- stats
    def stats(self) -> dict[str, Any]:
        nodes = dict(self._conn.execute(
            "SELECT type, COUNT(*) FROM nodes GROUP BY type").fetchall())
        edges = dict(self._conn.execute(
            "SELECT rel, COUNT(*) FROM edges GROUP BY rel").fetchall())
        return {"nodes": nodes, "edges": edges,
                "n_nodes": sum(nodes.values()), "n_edges": sum(edges.values())}

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [self._row_to_node(r).__dict__
                      for r in self._conn.execute("SELECT * FROM nodes")],
            "edges": [self._row_to_edge(r).__dict__
                      for r in self._conn.execute("SELECT * FROM edges")],
        }

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> Node:
        return Node(id=row["id"], type=row["type"], name=row["name"],
                    version=row["version"], digest=row["digest"],
                    attrs=json.loads(row["attrs"]), run_id=row["run_id"],
                    created_at=row["created_at"])

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> Edge:
        return Edge(id=row["id"], src=row["src"], dst=row["dst"], rel=row["rel"],
                    attrs=json.loads(row["attrs"]), run_id=row["run_id"],
                    created_at=row["created_at"])
