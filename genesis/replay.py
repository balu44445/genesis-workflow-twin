"""Concrete interpreter independent of the SMT encoding."""
from .model import Snapshot, digest, unsupported


def initial(snapshot: Snapshot, requester: str, assigned_approver: str) -> dict:
    people = {a.id: a for a in snapshot.actors}
    if requester not in people or "requester" not in people[requester].roles:
        raise ValueError("Requester is not eligible")
    if assigned_approver not in people or "approver" not in people[assigned_approver].roles:
        raise ValueError("Assigned approver is not eligible")
    return {"state": "draft", "requester": requester,
            "assigned_approver": assigned_approver, "approved_by": None}


def step(snapshot: Snapshot, state: dict, action: str, actor_id: str) -> dict:
    actor = next((a for a in snapshot.actors if a.id == actor_id), None)
    if actor is None:
        raise ValueError("Unknown actor")
    result = dict(state)
    if action == "submit" and state["state"] == "draft" and actor_id == state["requester"]:
        result["state"] = "pending"
    elif (action == "approve" and state["state"] == "pending"
          and actor_id == state["assigned_approver"] and "approver" in actor.roles
          and (not snapshot.policy.require_distinct_approver or actor_id != state["requester"])):
        result.update(state="approved", approved_by=actor_id)
    elif action == "fulfill" and state["state"] == "approved" and "fulfiller" in actor.roles:
        result["state"] = "fulfilled"
    else:
        raise ValueError("Transition guard rejected the action")
    return result


def violated(state: dict) -> bool:
    return state["state"] in ("approved", "fulfilled") and state["approved_by"] == state["requester"]


def replay(snapshot: Snapshot, evidence: dict) -> dict:
    if unsupported(snapshot):
        raise ValueError("Cannot replay unsupported semantics")
    if evidence.get("snapshot_sha256") != digest(snapshot):
        raise ValueError("Evidence does not match the snapshot hash")
    if evidence.get("status") != "violation":
        raise ValueError("Evidence must contain a violation")
    witness = evidence.get("counterexample", {})
    state = initial(snapshot, witness["requester"], witness["assigned_approver"])
    if state != witness["initial"]:
        raise ValueError("Invalid initial state")
    for event in witness["trace"]:
        if event["before"] != state:
            raise ValueError("Trace state mismatch")
        state = step(snapshot, state, event["action"], event["actor"])
        if state != event["after"]:
            raise ValueError("Trace effect mismatch")
    if not violated(state):
        raise ValueError("Trace does not violate segregation of duties")
    return {"reproduced": True, "steps": len(witness["trace"]), "final": state}
