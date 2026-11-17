"""Prepare target-specific setup without credentials or remote mutations."""
import json
from pathlib import Path
import re

from .model import Snapshot, digest


def prepare(alice, bob, carol, destination):
    ids = [alice, bob, carol]
    if len(set(ids)) != 3 or any(not re.fullmatch(r"[0-9a-f]{32}", i) for i in ids):
        raise ValueError("Provide three distinct, lowercase 32-character target sys_user IDs")
    base = json.loads((Path(__file__).with_name("static") / "fixed.json").read_text())
    for actor, identifier in zip(base["actors"], ids):
        actor["id"] = identifier
    base["source"] = {"kind": "servicenow_export",
                      "description": "Configured GENESIS PDI sample; not inferred platform behavior"}
    snapshot = Snapshot.model_validate(base)
    out = Path(destination)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(snapshot.model_dump_json(indent=2) + "\n")
    plan = {"kind": "offline_installation_plan", "target_tested": False,
            "snapshot_sha256": digest(snapshot), "policy": snapshot.policy.model_dump(),
            "required_tables": ["u_genesis_request", "u_genesis_action_claim"],
            "required_constraint": "UNIQUE u_genesis_action_claim.u_key",
            "manual_checks": ["Create/verify active users and explicit demo roles",
                              "Preview target update set; resolve collisions before commit",
                              "Install GenesisGuard and its admin-only claim table before new gateway",
                              "Check all API and table/field ACLs; remove temporary elevation",
                              "Save mapped manifest and record actual target API base",
                              "Read-only export and compare to manifest.json",
                              "Run main scenarios, security denials, and concurrent actor tests"],
            "live_calls_performed": 0}
    (out / "installation-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def check_export(actual: Snapshot, expected: Snapshot):
    if actual.source.kind != "servicenow_export":
        raise ValueError("Actual snapshot is not labeled as a ServiceNow export")
    if digest(actual) != digest(expected):
        raise ValueError("Export differs from the target manifest; compare actors, policy, revision and semantics")
    return {"matches": True, "snapshot_sha256": digest(actual),
            "scope": "Model export comparison only; does not validate ACLs, claim uniqueness, or concurrency"}
