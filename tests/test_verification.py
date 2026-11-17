from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from itertools import product
import json
import subprocess
import sys

import pytest
from pydantic import ValidationError
import z3

from genesis.model import Snapshot, digest, lower
from genesis.replay import initial, replay, step, violated
from genesis.verifier import verify


def enumerate_states(snapshot, bound=3):
    states = []
    for requester in snapshot.actors:
        for approver in snapshot.actors:
            try:
                states.append(initial(snapshot, requester.id, approver.id))
            except ValueError:
                pass
    visited = list(states)
    for _ in range(bound):
        next_states = []
        for state in states:
            for action in ('submit', 'approve', 'fulfill'):
                for actor in snapshot.actors:
                    try:
                        next_states.append(step(snapshot, state, action, actor.id))
                    except ValueError:
                        pass
        visited.extend(next_states)
        states = next_states
    return visited


def test_vulnerability_and_replay(snapshot):
    evidence = verify(snapshot)
    assert evidence['status'] == 'violation'
    assert evidence['shortest_depth'] == 2
    assert evidence['counterexample']['requester'] == 'alice'
    assert [e['action'] for e in evidence['counterexample']['trace']] == ['submit', 'approve']
    assert replay(snapshot, evidence)['reproduced'] is True
    assert evidence == verify(snapshot)


def test_fixed_and_happy_path(snapshot):
    snapshot.policy.require_distinct_approver = True
    assert verify(snapshot, 6)['status'] == 'no_violation_within_bound'
    state = initial(snapshot, 'alice', 'bob')
    for action, actor in [('submit', 'alice'), ('approve', 'bob'), ('fulfill', 'carol')]:
        state = step(snapshot, state, action, actor)
    assert state['state'] == 'fulfilled'
    assert not violated(state)
    self_request = step(snapshot, initial(snapshot, 'alice', 'alice'), 'submit', 'alice')
    with pytest.raises(ValueError):
        step(snapshot, self_request, 'approve', 'alice')


@pytest.mark.parametrize('bound', [0, 1])
def test_short_bound_does_not_claim_safety(snapshot, bound):
    result = verify(snapshot, bound)
    assert result['status'] == 'no_violation_within_bound'
    assert result['bound'] == bound
    assert 'not a platform safety proof' in result['reasons'][0]


@pytest.mark.parametrize('field,value', [
    ('semantics', 'javascript-arbitrary/v9'), ('schema_version', '2'),
    ('steps', ['submit', 'delegate', 'approve']), ('unsupported_features', ['async_business_rule'])])
def test_unsupported_is_inconclusive(raw, field, value):
    raw[field] = value
    model = Snapshot.model_validate(raw)
    assert verify(model)['status'] == 'inconclusive'
    with pytest.raises(ValueError):
        lower(model)


@pytest.mark.parametrize('change', ['duplicate', 'boolean-string', 'missing-role', 'unknown-field', 'too-many'])
def test_malformed_contract_rejected(raw, change):
    if change == 'duplicate':
        raw['actors'][1]['id'] = 'alice'
    elif change == 'boolean-string':
        raw['policy']['require_distinct_approver'] = 'false'
    elif change == 'missing-role':
        raw['actors'] = raw['actors'][:2]
    elif change == 'unknown-field':
        raw['unmodeled_guard'] = True
    else:
        raw['actors'] = raw['actors'] * 3
    with pytest.raises(ValidationError):
        Snapshot.model_validate(raw)


def test_tampering_and_snapshot_drift(snapshot):
    evidence = verify(snapshot)
    tampered = deepcopy(evidence)
    tampered['counterexample']['trace'][1]['actor'] = 'bob'
    with pytest.raises(ValueError):
        replay(snapshot, tampered)
    snapshot.policy.require_distinct_approver = True
    with pytest.raises(ValueError, match='hash'):
        replay(snapshot, evidence)


def test_solver_unknown_is_inconclusive(snapshot, monkeypatch):
    monkeypatch.setattr(z3.Solver, 'check', lambda *args: z3.unknown)
    assert verify(snapshot)['status'] == 'inconclusive'


def test_independent_z3_contexts(snapshot):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: verify(snapshot), range(12)))
    assert all(r == results[0] for r in results)


def test_smt_agrees_with_exhaustive_concrete_exploration(raw):
    roles = ['requester', 'approver', 'fulfiller']
    checked = 0
    for masks in product(range(1, 8), repeat=2):
        population = [{'id': f'u{i}', 'name': f'User {i}',
                       'roles': [role for bit, role in enumerate(roles) if mask & (1 << bit)]}
                      for i, mask in enumerate(masks)]
        if not all(any(role in p['roles'] for p in population) for role in roles):
            continue
        for fixed in (False, True):
            data = deepcopy(raw)
            data['actors'] = population
            data['policy']['require_distinct_approver'] = fixed
            model = Snapshot.model_validate(data)
            expected = any(violated(s) for s in enumerate_states(model))
            result = verify(model)
            assert (result['status'] == 'violation') == expected, (masks, fixed)
            assert result['status'] != 'inconclusive'
            checked += 1
    assert checked == 50


def test_cli_exit_codes(tmp_path):
    expected = [('examples/vulnerable.json', 2), ('examples/fixed.json', 0)]
    for file, code in expected:
        output = tmp_path / 'evidence.json'
        result = subprocess.run([sys.executable, '-m', 'genesis.cli', 'verify', file, '--out', str(output)], capture_output=True)
        assert result.returncode == code, result.stderr
        assert json.loads(output.read_text())['counterexample'] is not None if code == 2 else True


def test_hash_is_key_order_independent(raw):
    assert digest(Snapshot.model_validate(raw)) == digest(Snapshot.model_validate(dict(reversed(list(raw.items())))))
