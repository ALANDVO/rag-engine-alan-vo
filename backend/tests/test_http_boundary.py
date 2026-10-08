import base64
import hashlib
import secrets
from app.core.database import get_db, utc_now
from app.core.security import compute_pkce_challenge


def test_real_http_boundary_full_workflow(client, operator_headers, viewer_headers):
    # 1. Ingest via HTTP boundary
    doc_payload = {
        "name": "integration-spec.md",
        "text": "# Integration Spec\n\nThe full-stack system exposes typed JSON routes.\n\nDual dense and sparse representations ensure recall.",
        "collection": "integration-test",
    }
    ingest_res = client.post("/api/documents/ingest", json=doc_payload, headers=operator_headers)
    assert ingest_res.status_code == 201
    doc_data = ingest_res.json()
    doc_id = doc_data["id"]

    # 2. Read documents list via HTTP boundary
    list_res = client.get("/api/documents?collection=integration-test", headers=viewer_headers)
    assert list_res.status_code == 200
    assert any(d["id"] == doc_id for d in list_res.json()["items"])

    # 3. Hybrid search via HTTP boundary
    search_payload = {
        "query": "typed JSON routes",
        "collection": "integration-test",
        "top_k": 3,
    }
    search_res = client.post("/api/search", json=search_payload, headers=viewer_headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_results"] >= 1
    assert "typed JSON routes" in search_data["results"][0]["text"]

    # 4. Grounded Generation via HTTP boundary
    gen_payload = {
        "question": "What does the integration spec state about JSON routes?",
        "collection": "integration-test",
        "top_k": 3,
    }
    gen_res = client.post("/api/generate", json=gen_payload, headers=viewer_headers)
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["answer"]
    assert len(gen_data["citations"]) >= 1
    assert gen_data["faithfulness"]["faithfulness_score"] > 0.0


def test_oidc_pkce_protocol_fixture(client):
    # 1. Generate compliant PKCE code_verifier (43-128 chars) and challenge
    code_verifier = secrets.token_urlsafe(50)
    code_challenge = compute_pkce_challenge(code_verifier)

    # 2. Assert rejection on invalid/too short code_verifier
    short_verifier = "short_invalid"
    reject_res = client.post(
        "/api/auth/token",
        json={
            "code": "auth-code-12345",
            "code_verifier": short_verifier,
            "redirect_uri": "http://localhost:3000/callback",
        },
    )
    assert reject_res.status_code == 400

    # 3. Exchange valid authorization code + verifier
    exchange_res = client.post(
        "/api/auth/token",
        json={
            "code": "valid-auth-code-with-operator-role",
            "code_verifier": code_verifier,
            "redirect_uri": "http://localhost:3000/callback",
        },
    )
    assert exchange_res.status_code == 200
    token_data = exchange_res.json()
    access_token = token_data["access_token"]
    assert access_token

    # 4. Propagate issued token into an authorized API request
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    me_res = client.get("/api/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["effective_role"] in ("operator", "admin", "viewer")


def test_sqlite_persistence_and_transactions():
    now = utc_now()
    # Test persistent transactional commit
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO collections (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("tx-test", "Transactional test", now, now),
        )

    # Verify persisted in new connection
    with get_db() as conn:
        row = conn.execute("SELECT name FROM collections WHERE name = 'tx-test'").fetchone()
        assert row is not None
        assert row["name"] == "tx-test"
