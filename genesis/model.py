"""Strict input contract and explicit lowering boundary; no JavaScript inference."""
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SEMANTICS = "genesis-sequential-approval/v1"
STEPS = ["submit", "approve", "fulfill"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Actor(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)
    roles: list[Literal["requester", "approver", "fulfiller"]] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_roles(self):
        if len(self.roles) != len(set(self.roles)):
            raise ValueError("Actor roles must be unique")
        return self


class Policy(StrictModel):
    require_distinct_approver: bool


class Source(StrictModel):
    kind: Literal["fixture", "servicenow_export"]
    description: str = Field(max_length=500)


class Snapshot(StrictModel):
    schema_version: str = Field(max_length=20)
    semantics: str = Field(max_length=100)
    workflow_id: str = Field(min_length=1, max_length=100)
    revision: str = Field(min_length=1, max_length=100)
    source: Source
    steps: list[str] = Field(max_length=10)
    actors: list[Actor] = Field(min_length=1, max_length=8)
    policy: Policy
    unsupported_features: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def valid_population(self):
        ids = [a.id for a in self.actors]
        if len(ids) != len(set(ids)):
            raise ValueError("Actor IDs must be unique")
        for role in ("requester", "approver", "fulfiller"):
            if not any(role in a.roles for a in self.actors):
                raise ValueError(f"At least one actor with {role} eligibility is required")
        return self


def digest(snapshot: Snapshot) -> str:
    payload = json.dumps(snapshot.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def unsupported(snapshot: Snapshot) -> list[str]:
    reasons = list(snapshot.unsupported_features)
    if snapshot.schema_version != "1":
        reasons.append("Unsupported schema version")
    if snapshot.semantics != SEMANTICS:
        reasons.append("Unsupported transition semantics")
    if snapshot.steps != STEPS:
        reasons.append("Only submit -> approve -> fulfill is supported")
    return reasons


def lower(snapshot: Snapshot) -> dict:
    reasons = unsupported(snapshot)
    if reasons:
        raise ValueError("; ".join(reasons))
    return {
        "semantics": SEMANTICS,
        "snapshot_sha256": digest(snapshot),
        "states": ["draft", "pending", "approved", "fulfilled"],
        "transitions": [
            {"action": "submit", "from": "draft", "to": "pending", "guard": "actor == requester"},
            {"action": "approve", "from": "pending", "to": "approved",
             "guard": "actor == assigned_approver AND eligible(actor, approver)" +
             (" AND actor != requester" if snapshot.policy.require_distinct_approver else ""),
             "effect": "approved_by := actor"},
            {"action": "fulfill", "from": "approved", "to": "fulfilled", "guard": "eligible(actor, fulfiller)"},
        ],
        "invariant": "state in {approved, fulfilled} => approved_by != requester",
        "eligibility": "Finite configured actor roles, not inferred ServiceNow ACLs or inherited roles",
    }
