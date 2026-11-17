"""Transactional local demo runtime. This store never writes to ServiceNow."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4
from contextvars import ContextVar

visitor_database = ContextVar('visitor_database', default=None)

from .model import Snapshot, digest, unsupported
from .replay import initial, step


class RuntimeErrorResponse(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    path = Path(visitor_database.get() or os.environ.get("GENESIS_DB", "pdi-local/dashboard.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS requests (
          id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
          runtime TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL REFERENCES requests(id),
          occurred_at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
          outcome TEXT NOT NULL, reason TEXT NOT NULL, before_state TEXT, after_state TEXT,
          version INTEGER NOT NULL);
    """)
    try:
        yield db
    finally:
        if db.in_transaction:
            db.rollback()
        db.close()


def decode(row):
    return {**dict(row), "snapshot": json.loads(row["snapshot"]), "runtime": json.loads(row["runtime"])}


def event(db, record, actor, action, outcome, reason, before, after, version):
    db.execute("INSERT INTO events(request_id,occurred_at,actor,action,outcome,reason,before_state,after_state,version) "
               "VALUES(?,?,?,?,?,?,?,?,?)", (record, now(), actor, action, outcome, reason,
               json.dumps(before), json.dumps(after), version))


def create(snapshot: Snapshot, actor: str, assigned: str):
    if unsupported(snapshot):
        raise RuntimeErrorResponse(422, "This runtime cannot execute unsupported workflow semantics")
    try:
        state = initial(snapshot, actor, assigned)
    except ValueError as exc:
        raise RuntimeErrorResponse(403, str(exc)) from exc
    identifier = uuid4().hex
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO requests VALUES(?,?,?,?,?,?)", (identifier,
                   snapshot.model_dump_json(), digest(snapshot), json.dumps(state), 0, now()))
        event(db, identifier, actor, "create", "accepted", "Eligible requester and approver", None, state, 0)
        db.commit()
    return get(identifier)


def get(identifier):
    with connection() as db:
        row = db.execute("SELECT * FROM requests WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise RuntimeErrorResponse(404, "Request not found")
        result = decode(row)
        result["events"] = [dict(e) for e in db.execute(
            "SELECT * FROM events WHERE request_id=? ORDER BY sequence", (identifier,))]
        for e in result["events"]:
            for key in ("before_state", "after_state"):
                e[key] = json.loads(e[key])
        return result


def listing():
    with connection() as db:
        return [decode(r) for r in db.execute("SELECT * FROM requests ORDER BY created_at DESC LIMIT 100")]


def act(identifier, actor, action, expected_version):
    failure = None
    with connection() as db:
        # A write transaction serializes contenders across processes using the same database.
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM requests WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise RuntimeErrorResponse(404, "Request not found")
        before = json.loads(row["runtime"])
        snapshot = Snapshot.model_validate_json(row["snapshot"])
        if expected_version != row["version"]:
            failure = RuntimeErrorResponse(409, "Request changed. Refresh before trying again")
        else:
            try:
                after = step(snapshot, before, action, actor)
            except ValueError:
                failure = RuntimeErrorResponse(403, rejection_reason(snapshot, before, action, actor))
        if failure:
            event(db, identifier, actor, action, "rejected", failure.message,
                  before, before, row["version"])
        else:
            db.execute("UPDATE requests SET runtime=?,version=version+1 WHERE id=?",
                       (json.dumps(after), identifier))
            event(db, identifier, actor, action, "accepted", "Workflow guard satisfied",
                  before, after, row["version"] + 1)
        db.commit()
    if failure:
        raise failure
    return get(identifier)


def rejection_reason(snapshot, state, action, actor):
    people = {p.id: p for p in snapshot.actors}
    if actor not in people:
        return "The acting user is absent from this request's policy snapshot"
    expected = {"submit": "draft", "approve": "pending", "fulfill": "approved"}
    if state["state"] != expected.get(action):
        return f"{action.capitalize()} is unavailable while the request is {state['state']}"
    if action == "submit":
        return "Only the requester can submit this request"
    if action == "approve":
        if actor != state["assigned_approver"]:
            return "Only the assigned approver can approve this request"
        if "approver" not in people[actor].roles:
            return "The acting user is not eligible to approve"
        return "The distinct-approver policy blocks requester self-approval"
    return "The acting user is not eligible to fulfill"
