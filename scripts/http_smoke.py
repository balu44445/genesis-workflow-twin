"""Run against a real local Uvicorn process: python scripts/http_smoke.py."""
import json
from pathlib import Path

import httpx

root = Path(__file__).resolve().parents[1]
with httpx.Client(base_url='http://127.0.0.1:8000', timeout=15, trust_env=False) as client:
    health = client.get('/health')
    health.raise_for_status()
    assert health.json()['status'] == 'ok'
    assert client.get('/docs').status_code == 200
    assert client.get('/openapi.json').status_code == 200
    statuses = {}
    for variant in ('vulnerable', 'fixed'):
        snapshot = json.loads((root / 'examples' / f'{variant}.json').read_text())
        response = client.post('/verify', json={'snapshot': snapshot, 'bound': 3})
        response.raise_for_status()
        evidence = response.json()
        statuses[variant] = evidence['status']
        if variant == 'vulnerable':
            response = client.post('/replay', json={'snapshot': snapshot, 'evidence': evidence})
            response.raise_for_status()
            assert response.json()['reproduced'] is True
    assert statuses == {'vulnerable': 'violation', 'fixed': 'no_violation_within_bound'}
    snapshot['unsupported_features'] = ['delegation']
    assert client.post('/verify', json={'snapshot': snapshot}).json()['status'] == 'inconclusive'
    print(json.dumps({'http_smoke': 'passed', **statuses}, indent=2))
