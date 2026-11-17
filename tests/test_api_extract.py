from copy import deepcopy

from fastapi.testclient import TestClient
import httpx
import pytest

from genesis.api import app
from genesis.extract import extract

client = TestClient(app)
URL = 'https://dev12345.service-now.com/api/global/genesis/model'


def test_api_end_to_end(raw):
    assert client.get('/health').status_code == 200
    response = client.post('/verify', json={'snapshot': raw})
    assert response.status_code == 200
    assert response.json()['status'] == 'violation'
    assert client.post('/replay', json={'snapshot': raw, 'evidence': response.json()}).json()['reproduced']
    assert len(client.post('/model', json=raw).json()['transitions']) == 3
    raw['policy']['require_distinct_approver'] = True
    assert client.post('/verify', json={'snapshot': raw}).json()['status'] == 'no_violation_within_bound'


def test_api_rejects_bad_input(raw):
    for bound in (-1, 7, '3', True):
        assert client.post('/verify', json={'snapshot': raw, 'bound': bound}).status_code == 422
    assert client.post('/replay', json={'snapshot': raw, 'evidence': {}}).status_code == 422
    raw['unsupported_features'] = ['custom_script']
    assert client.post('/verify', json={'snapshot': raw}).json()['status'] == 'inconclusive'


@pytest.mark.parametrize('wrapped', [False, True])
def test_read_only_export(raw, wrapped):
    raw['source']['kind'] = 'servicenow_export'
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={'result': raw} if wrapped else raw)
    snapshot = extract(URL, token='fake-test-token', transport=httpx.MockTransport(handler))
    assert snapshot.actors[0].id == 'alice'
    assert len(calls) == 1 and calls[0].method == 'GET'
    assert calls[0].headers['Authorization'] == 'Bearer fake-test-token'


@pytest.mark.parametrize('url', ['http://dev.service-now.com/api/x', 'https://attacker.test/api/x',
                               'https://dev.service-now.com.evil.test/api/x', 'https://user:pass@dev.service-now.com/api/x'])
def test_adapter_url_boundary(url):
    with pytest.raises(ValueError):
        extract(url, token='fake-test-token')


@pytest.mark.parametrize('status', [302, 401, 403, 500])
def test_export_failures_are_explicit(status):
    with pytest.raises(ValueError, match=f'HTTP {status}'):
        extract(URL, token='fake-test-token', transport=httpx.MockTransport(lambda _: httpx.Response(status)))


def test_fixture_cannot_be_claimed_as_live_export(raw):
    with pytest.raises(ValueError, match='offline fixture'):
        extract(URL, token='fake-test-token', transport=httpx.MockTransport(lambda _: httpx.Response(200, json=raw)))


def test_oversized_export():
    with pytest.raises(ValueError, match='64 KiB'):
        extract(URL, token='fake-test-token', transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b'x' * 65537)))
