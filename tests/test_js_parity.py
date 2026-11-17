import json
import shutil
import subprocess

import pytest

from genesis.replay import initial, step
from test_verification import enumerate_states


def test_servicenow_core_matches_concrete_model(snapshot):
    if not shutil.which('node'):
        pytest.fail('Node.js is required to validate the actual ServiceNow GenesisCore.js')
    cases, expected = [], []
    for fixed in (False, True):
        snapshot.policy.require_distinct_approver = fixed
        raw = snapshot.model_dump()
        for requester in ('alice', 'bob', 'carol', 'unknown'):
            for assigned in ('alice', 'bob', 'carol', 'unknown'):
                cases.append({'initial': True, 'snapshot': raw, 'requester': requester, 'assigned': assigned})
                try:
                    expected.append({'ok': True, 'state': initial(snapshot, requester, assigned)})
                except ValueError:
                    expected.append({'ok': False})
        for state in enumerate_states(snapshot):
            for action in ('submit', 'approve', 'fulfill', 'delegate'):
                for actor in ('alice', 'bob', 'carol', 'unknown'):
                    cases.append({'snapshot': raw, 'state': state, 'action': action, 'actor': actor})
                    try:
                        expected.append({'ok': True, 'state': step(snapshot, state, action, actor)})
                    except ValueError:
                        expected.append({'ok': False})
    result = subprocess.run(['node', 'scripts/js_core_runner.cjs'], input=json.dumps(cases),
                            text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == expected
    assert len(cases) > 200
