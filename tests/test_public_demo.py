from fastapi.testclient import TestClient
from genesis.api import app
from genesis.public import PublicDemo


def test_public_visitor_isolation_and_boundaries(tmp_path, monkeypatch, raw):
    monkeypatch.setenv('GENESIS_SESSION_SECRET', 'test-secret-' * 4)
    monkeypatch.setenv('GENESIS_PUBLIC_DATA', str(tmp_path))
    monkeypatch.setenv('GENESIS_PUBLIC_REQUIRE_HTTPS', 'false')
    monkeypatch.setenv('GENESIS_PUBLIC_MODE', 'true')
    public = PublicDemo(app)
    alice, bob = TestClient(public), TestClient(public)
    body = {'snapshot': raw, 'actor': 'alice', 'assigned_approver': 'bob'}
    r = alice.post('/demo/requests', json=body)
    assert r.status_code == 201, r.text
    identifier = r.json()['id']
    assert len(alice.get('/demo/requests').json()) == 1
    assert bob.get('/demo/requests').json() == []
    assert bob.get('/demo/requests/' + identifier).status_code == 404
    assert alice.post('/explain', json={'snapshot': raw, 'external_ai': True}).status_code == 422
    assert alice.post('/verify', json={'snapshot': raw, 'bound': 6}).status_code == 422
    raw['source']['description'] = 'private data'
    assert alice.post('/verify', json={'snapshot': raw}).status_code == 422
    assert alice.post('/verify', content=b'x'*65537).status_code == 413
    assert alice.post('/model', json={}).status_code == 404
    assert alice.get('/docs').status_code == 404
    assert alice.get('/demo/config').json()['mode'] == 'public_synthetic_demo'
    assert len(public.sessions) == 2
    for _ in range(65):
        result = alice.get('/health')
    assert result.status_code == 200
    for _ in range(65):
        result = alice.get('/demo/config')
    assert result.status_code == 429


def test_public_requires_secret(monkeypatch):
    monkeypatch.delenv('GENESIS_SESSION_SECRET', raising=False)
    assert TestClient(PublicDemo(app)).get('/').status_code == 503


def test_public_rejects_before_allocating_and_requires_https(tmp_path, monkeypatch):
    monkeypatch.setenv('GENESIS_SESSION_SECRET', 'test-secret-' * 4)
    monkeypatch.setenv('GENESIS_PUBLIC_DATA', str(tmp_path))
    public = PublicDemo(app)
    client = TestClient(public)
    assert client.get('/').status_code == 400
    assert public.sessions == {}
    assert client.post('/verify', content=b'not json').status_code == 400
    assert public.sessions == {}
    secure = TestClient(public, base_url='https://testserver')
    assert secure.post('/verify', content=b'not json').status_code == 415
    assert public.sessions == {}
    response = secure.get('/')
    assert response.status_code == 200
    assert '; Secure' in response.headers['set-cookie']
    assert response.headers['strict-transport-security'] == 'max-age=31536000; includeSubDomains'
    assert response.headers['permissions-policy'] == 'camera=(), geolocation=(), microphone=()'
