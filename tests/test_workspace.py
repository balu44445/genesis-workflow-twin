from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import httpx
import pytest

from genesis.api import app
from genesis.explain import ai_explanation
from genesis.install import prepare, check_export
from genesis.model import Snapshot
from genesis.verifier import verify
from genesis import runtime


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GENESIS_DB", str(tmp_path / "workspace.sqlite3"))
    monkeypatch.delenv("GENESIS_AI_ENABLED", raising=False)
    return TestClient(app)


def make(client, raw, assigned="bob"):
    raw["policy"]["require_distinct_approver"] = True
    r = client.post("/demo/requests", json={"snapshot": raw, "actor": "alice", "assigned_approver": assigned})
    assert r.status_code == 201, r.text
    return r.json()


def action(client, record, actor, name, version):
    return client.post(f"/demo/requests/{record}/actions", json={
        "actor": actor, "action": name, "expected_version": version})


def test_atomic_concurrent_actions_have_one_winner(client, raw):
    record = make(client, raw)["id"]
    assert action(client, record, "alice", "submit", 0).status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: action(client, record, "bob", "approve", 1), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]
    saved = client.get(f"/demo/requests/{record}").json()
    assert saved["runtime"]["state"] == "approved"
    assert saved["runtime"]["approved_by"] == "bob"
    assert saved["version"] == 2
    assert [e["outcome"] for e in saved["events"]].count("rejected") == 1
    assert action(client, record, "carol", "fulfill", 2).json()["runtime"]["state"] == "fulfilled"


def test_rejection_preserves_state_and_records_reason(client, raw):
    record = make(client, raw, "alice")["id"]
    action(client, record, "alice", "submit", 0)
    denial = action(client, record, "alice", "approve", 1)
    assert denial.status_code == 403
    assert "self-approval" in denial.json()["detail"]
    saved = client.get(f"/demo/requests/{record}").json()
    assert saved["version"] == 1 and saved["runtime"]["approved_by"] is None
    assert saved["events"][-1]["before_state"] == saved["events"][-1]["after_state"]
    assert saved["events"][-1]["outcome"] == "rejected"


def test_actor_and_policy_boundaries(client, raw):
    record = make(client, raw)["id"]
    assert action(client, record, "outsider", "submit", 0).status_code == 403
    assert action(client, record, "bob", "submit", 0).status_code == 403
    assert action(client, record, "carol", "fulfill", 0).status_code == 403
    raw["unsupported_features"] = ["delegation"]
    assert client.post("/demo/requests", json={"snapshot": raw, "actor": "alice", "assigned_approver": "bob"}).status_code == 422
    assert client.post("/verify", json={"snapshot": raw}).json()["status"] == "inconclusive"


def test_snapshots_are_immutable_and_timeline_is_durable(client, raw):
    created = make(client, raw)
    raw["policy"]["require_distinct_approver"] = False
    saved = TestClient(app).get("/demo/requests/" + created["id"]).json()
    assert saved["snapshot"]["policy"]["require_distinct_approver"] is True
    assert saved["snapshot_hash"] == created["snapshot_hash"]
    assert saved["events"][0]["action"] == "create"


def test_event_failure_rolls_back_state_and_version(client, raw, monkeypatch):
    record = make(client, raw)["id"]
    def failing_event(*args, **kwargs):
        raise RuntimeError("Simulated evidence write failure")
    with monkeypatch.context() as scoped:
        scoped.setattr(runtime, "event", failing_event)
        with pytest.raises(RuntimeError, match="evidence write"):
            runtime.act(record, "alice", "submit", 0)
    saved = runtime.get(record)
    assert saved["version"] == 0 and saved["runtime"]["state"] == "draft"
    assert len(saved["events"]) == 1
    assert action(client, record, "alice", "submit", 0).status_code == 200


def test_provider_errors_do_not_expose_secrets(client, raw, monkeypatch):
    monkeypatch.setattr("genesis.api.ai_enabled", lambda: True)
    def failing_provider(evidence):
        raise ValueError("sensitive-provider-detail")
    monkeypatch.setattr("genesis.api.ai_explanation", failing_provider)
    result = client.post("/explain", json={"snapshot": raw, "external_ai": True})
    assert result.status_code == 503 and "sensitive-provider-detail" not in result.text


def test_preview_never_applies_and_bounded_explanation_is_honest(client, raw):
    proposed = deepcopy(raw)
    proposed["policy"]["require_distinct_approver"] = True
    r = client.post("/compare", json={"snapshot": raw, "proposed": proposed}).json()
    assert r["current"]["status"] == "violation"
    assert r["proposed"]["status"] == "no_violation_within_bound"
    assert r["changes"][0]["field"] == "policy" and r["applied"] is False
    assert client.get("/demo/requests").json() == []
    explanation = client.post("/explain", json={"snapshot": proposed}).json()["explanation"]
    assert explanation["mode"] == "local" and "0–3" in explanation["text"]
    assert "does not certify" in explanation["text"]
    assert client.post("/explain", json={"snapshot": proposed, "external_ai": True}).status_code == 409


def test_ai_adapter_sends_only_derived_anonymous_facts(monkeypatch, raw):
    monkeypatch.setenv("GENESIS_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "mock-only-secret")
    monkeypatch.setenv("GENESIS_AI_MODEL", "mock-model")
    raw["source"]["description"] = "PRIVATE SOURCE"
    calls = []
    def provider(request):
        calls.append(request)
        return httpx.Response(200, json={"output": [{"type": "message", "content": [
            {"type": "output_text", "text": "Mock explanation. Bounded sequential model only."}]}]})
    result = ai_explanation(verify(Snapshot.model_validate(raw)), transport=httpx.MockTransport(provider))
    assert result["mode"] == "external_ai" and len(calls) == 1
    sent = json.loads(calls[0].content)
    assert sent["store"] is False
    assert "PRIVATE SOURCE" not in calls[0].content.decode()
    assert "alice" not in calls[0].content.decode().lower()
    assert "snapshot" not in json.loads(sent["input"])


def test_workspace_browser_security(client):
    r = client.get("/")
    assert r.status_code == 200 and "Trust the evidence" in r.text
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert client.get("/assets/app.js").status_code == 200
    assert client.post("/verify", json={}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.get("/", headers={"Host": "untrusted.example"}).status_code == 400
    assert client.post("/demo/requests", content="x").status_code == 415
    docs = client.get("/docs")
    assert docs.status_code == 200 and '<script nonce="' in docs.text
    nonce = docs.text.split('<script nonce="')[1].split('"')[0]
    assert "'nonce-" + nonce + "'" in docs.headers["content-security-policy"]
    assert "cdn.jsdelivr.net" not in r.headers["content-security-policy"]


def test_target_installation_plan_validates_ids_and_export(tmp_path):
    ids = [str(i) * 32 for i in (1, 2, 3)]
    plan = prepare(*ids, tmp_path)
    snapshot = Snapshot.model_validate_json((tmp_path / "manifest.json").read_text())
    assert plan["live_calls_performed"] == 0 and not plan["target_tested"]
    assert [a.id for a in snapshot.actors] == ids
    assert check_export(snapshot, snapshot)["matches"]
    changed = snapshot.model_copy(update={"revision": "different"})
    with pytest.raises(ValueError, match="differs"):
        check_export(changed, snapshot)
    with pytest.raises(ValueError):
        prepare(ids[0], ids[0], ids[2], tmp_path)
