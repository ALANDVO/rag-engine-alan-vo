from app.services.rag_engine import chunk_text


async def test_update_collection_rename_cascades(client, operator_headers, viewer_headers):
    # Create an operator-owned collection
    create = await client.post(
        "/api/collections",
        json={"name": "rename-src", "description": "source"},
        headers=operator_headers,
    )
    assert create.status_code == 201

    # Ingest a document so documents/chunks reference the collection
    ingest = await client.post(
        "/api/documents/ingest",
        json={
            "collection": "rename-src",
            "name": "doc.md",
            "text": "Alpha beta gamma content about retrieval systems.\n\nSecond paragraph about dense vectors.",
        },
        headers=operator_headers,
    )
    assert ingest.status_code == 201

    # Rename the collection and update its description
    patch = await client.patch(
        "/api/collections/rename-src",
        json={"new_name": "rename-dst", "description": "renamed"},
        headers=operator_headers,
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["name"] == "rename-dst"
    assert body["description"] == "renamed"
    assert body["document_count"] == 1

    # Original name no longer lists
    colls = await client.get("/api/collections", headers=viewer_headers)
    names = [c["name"] for c in colls.json()["items"]]
    assert "rename-src" not in names
    assert "rename-dst" in names

    # Documents now report the new collection (FK cascade integrity)
    docs = await client.get("/api/documents?collection=rename-dst", headers=viewer_headers)
    assert docs.status_code == 200
    assert docs.json()["total"] == 1

    # Search still works against the renamed collection
    search = await client.post(
        "/api/search",
        json={"query": "retrieval systems", "collection": "rename-dst"},
        headers=viewer_headers,
    )
    assert search.status_code == 200
    assert search.json()["total_results"] >= 1


async def test_update_collection_conflicts_and_not_found(client, operator_headers):
    await client.post("/api/collections", json={"name": "coll-a"}, headers=operator_headers)
    await client.post("/api/collections", json={"name": "coll-b"}, headers=operator_headers)

    # Conflict: rename onto an existing name
    conflict = await client.patch(
        "/api/collections/coll-a",
        json={"new_name": "coll-b"},
        headers=operator_headers,
    )
    assert conflict.status_code == 409

    # Not found: source collection missing
    missing = await client.patch(
        "/api/collections/does-not-exist",
        json={"new_name": "whatever"},
        headers=operator_headers,
    )
    assert missing.status_code == 404

    # Viewer forbidden
    from app.core.security import create_demo_token

    viewer = create_demo_token(user_id="v", role="viewer")
    forbidden = await client.patch(
        "/api/collections/coll-a",
        json={"new_name": "coll-c"},
        headers={"Authorization": f"Bearer {viewer}"},
    )
    assert forbidden.status_code == 403
