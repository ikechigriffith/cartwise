from fastapi.testclient import TestClient

from app.main import app


def test_admin_store_candidates_requires_token_when_configured(monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-token")
    client = TestClient(app)

    response = client.get("/admin/store-candidates")
    assert response.status_code == 401

    response = client.get("/admin/store-candidates", headers={"X-Admin-Token": "test-token"})
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "counts_by_status" in body

    response = client.get("/admin/product-selection-reviews", headers={"X-Admin-Token": "test-token"})
    assert response.status_code == 200
    assert "items" in response.json()


def test_public_reference_endpoints_are_available():
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/retailers?limit=1").status_code == 200
    assert client.get("/stores?limit=1").status_code == 200
    assert client.get("/products/search?q=milo&limit=1").status_code == 200
