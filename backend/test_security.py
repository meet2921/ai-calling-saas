import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.parametrize("payload", [
    "' OR 1=1 --",
    "' OR '1'='1",
    "'; DROP TABLE users; --",
])

def test_sql_injection_on_login(payload):

    response = client.post("/api/auth/login", json={
        "org_slug": "test-org",
        "email": payload,
        "password": "test"
    })

    assert response.status_code in [401, 422]

    data = response.json()

    if isinstance(data, dict):
        assert "access_token" not in data