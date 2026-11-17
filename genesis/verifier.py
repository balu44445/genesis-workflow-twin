"""Finite-domain bounded model checker with shortest, canonical witnesses."""
from time import monotonic

import z3

from .model import Snapshot, digest, unsupported
from .replay import initial, replay, step


def verify(snapshot: Snapshot, bound: int = 3, timeout_ms: int = 2000) -> dict:
    if type(bound) is not int or not 0 <= bound <= 6:
        raise ValueError("bound must be an integer in [0, 6]")
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 10000:
        raise ValueError("timeout_ms must be an integer in [1, 10000]")
    result = {
        "status": "inconclusive", "property": "requester_must_not_approve_own_request",
        "snapshot_sha256": digest(snapshot), "bound": bound,
        "scope": "One sequential request, fixed configured identities and eligibility; model evidence only",
        "solver_version": z3.get_version_string(), "counterexample": None,
    }
    reasons = unsupported(snapshot)
    if reasons:
        return dict(result, reasons=reasons)
    deadline = monotonic() + timeout_ms / 1000
    # Each call has its own context: concurrent FastAPI requests never share Z3 ASTs.
    ctx = z3.Context()
    actors = sorted(snapshot.actors, key=lambda a: a.id)
    n = len(actors)
    eligible = {r: [i for i, a in enumerate(actors) if r in a.roles]
                for r in ("requester", "approver", "fulfiller")}

    def member(v, choices):
        return z3.Or(*[v == i for i in choices]) if choices else z3.BoolVal(False, ctx)

    def check(solver):
        remaining = int((deadline - monotonic()) * 1000)
        if remaining <= 0:
            return z3.unknown
        solver.set(timeout=max(1, remaining))
        return solver.check()

    for depth in range(bound + 1):
        solver = z3.Solver(ctx=ctx)
        requester, assigned = z3.Ints("requester assigned", ctx=ctx)
        phases = [z3.Int(f"phase_{t}", ctx) for t in range(depth + 1)]
        approved = [z3.Int(f"approved_{t}", ctx) for t in range(depth + 1)]
        acting = [z3.Int(f"actor_{t}", ctx) for t in range(depth)]
        solver.add(member(requester, eligible["requester"]), member(assigned, eligible["approver"]))
        solver.add(phases[0] == 0, approved[0] == -1)
        for t, actor in enumerate(acting):
            solver.add(actor >= 0, actor < n)
            distinct = actor != requester if snapshot.policy.require_distinct_approver else z3.BoolVal(True, ctx)
            solver.add(z3.Or(
                z3.And(phases[t] == 0, actor == requester, phases[t+1] == 1, approved[t+1] == approved[t]),
                z3.And(phases[t] == 1, actor == assigned, member(actor, eligible["approver"]),
                       distinct, phases[t+1] == 2, approved[t+1] == actor),
                z3.And(phases[t] == 2, member(actor, eligible["fulfiller"]),
                       phases[t+1] == 3, approved[t+1] == approved[t]),
            ))
        solver.add(phases[-1] >= 2, approved[-1] == requester)
        answer = check(solver)
        if answer == z3.unknown:
            return dict(result, reasons=["Solver returned unknown or the total time budget expired"], checked_depth=depth)
        if answer == z3.unsat:
            continue
        # Freeze the lexicographically least identity vector to make evidence reproducible.
        for variable in [requester, assigned, *acting]:
            for value in range(n):
                solver.push()
                solver.add(variable == value)
                answer = check(solver)
                solver.pop()
                if answer == z3.unknown:
                    return dict(result, reasons=["Time budget expired while canonicalizing the witness"])
                if answer == z3.sat:
                    solver.add(variable == value)
                    break
        if check(solver) != z3.sat:
            return dict(result, reasons=["Could not finalize witness within the time budget"])
        model = solver.model()
        identity = lambda v: actors[model.eval(v).as_long()].id
        requester_id, assigned_id = identity(requester), identity(assigned)
        state = initial(snapshot, requester_id, assigned_id)
        witness = {"requester": requester_id, "assigned_approver": assigned_id,
                   "initial": dict(state), "trace": []}
        for t, variable in enumerate(acting):
            action = ("submit", "approve", "fulfill")[model.eval(phases[t]).as_long()]
            actor_id = identity(variable)
            after = step(snapshot, state, action, actor_id)
            witness["trace"].append({"action": action, "actor": actor_id,
                                     "before": state, "after": after})
            state = after
        result.update(status="violation", counterexample=witness, shortest_depth=depth)
        result["replay"] = replay(snapshot, result)
        return result
    return dict(result, status="no_violation_within_bound", checked_depth=bound,
                reasons=[f"No counterexample at depths 0..{bound}; this is not a platform safety proof"])
