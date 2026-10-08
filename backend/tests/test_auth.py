import pytest
from app.core.config import Settings


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/documents")
    assert resp.status_code == 401
    assert "Missing Bearer" in resp.json()["detail"]


def test_invalid_token_rejected(client):
    headers = {"Authorization": "Bearer invalid.token.payload"}
    resp = client.get("/api/documents", headers=headers)
    assert resp.status_code == 401


def test_role_denial_viewer_cannot_ingest(client, viewer_headers):
    payload = {
        "name": "test.txt",
        "text": "Sample text for ingestion.",
        "collection": "default"
    }
    resp = client.post("/api/documents/ingest", json=payload, headers=viewer_headers)
    assert resp.status_code == 403
    assert "Insufficient permissions" in resp.json()["detail"]


def test_role_denial_viewer_cannot_delete(client, viewer_headers):
    resp = client.delete("/api/documents/doc-12345", headers=viewer_headers)
    assert resp.status_code == 403


def test_admin_audit_access_denial_and_grant(client, viewer_headers, admin_headers):
    resp_viewer = client.get("/api/audit", headers=viewer_headers)
    assert resp_viewer.status_code == 403

    resp_admin = client.get("/api/audit", headers=admin_headers)
    assert resp_admin.status_code == 200
    assert "entries" in resp_admin.json()


def test_demo_mode_refused_in_production():
    with pytest.raises(ValueError, match="Demo mode cannot be enabled in production"):
        s = Settings(demo_mode=True, environment="production")
        s.validate_environment()
