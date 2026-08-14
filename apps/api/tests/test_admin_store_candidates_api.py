from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.deps import get_db
from app.main import app


def test_admin_store_candidates_requires_token_when_configured(monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-token")
    client = TestClient(app)

    response = client.get("/admin/store-candidates")
    assert response.status_code == 401

    mock_db = MagicMock()
    mock_db.execute.return_value.all.return_value = []
    mock_db.execute.return_value.scalar_one.return_value = 0
    mock_db.query.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []
    mock_db.scalar.return_value = 0
    mock_db.scalars.return_value.all.return_value = []

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/admin/store-candidates", headers={"X-Admin-Token": "test-token"})
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "counts_by_status" in body

        response = client.get("/admin/product-selection-reviews", headers={"X-Admin-Token": "test-token"})
        assert response.status_code == 200
        assert "items" in response.json()
    finally:
        app.dependency_overrides.clear()


def test_public_reference_endpoints_are_available():
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = []
    mock_db.query.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []
    mock_db.query.return_value.join.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)

        assert client.get("/health").status_code == 200
        assert client.get("/retailers?limit=1").status_code == 200
        assert client.get("/stores?limit=1").status_code == 200
        assert client.get("/products/search?q=milo&limit=1").status_code == 200
    finally:
        app.dependency_overrides.clear()
