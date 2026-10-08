def test_ingest_document_success(client, operator_headers):
    payload = {
        "name": "engine-overview.md",
        "text": "# Engine Overview\n\nThe RAG engine provides hybrid retrieval combining dense and sparse indexers.\n\nParagraph two covers citations.",
        "collection": "test-coll",
        "chunk_size": 500,
        "chunk_overlap": 50,
    }

    resp = client.post("/api/documents/ingest", json=payload, headers=operator_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "engine-overview.md"
    assert data["collection"] == "test-coll"
    assert data["chunk_count"] >= 1
    assert "id" in data


def test_malformed_empty_document_rejected(client, operator_headers):
    payload = {
        "name": "empty.md",
        "text": "   ",
        "collection": "default",
    }
    resp = client.post("/api/documents/ingest", json=payload, headers=operator_headers)
    assert resp.status_code == 422


def test_list_and_get_chunks(client, operator_headers, viewer_headers):
    # Ingest a doc
    payload = {
        "name": "guide.md",
        "text": (
            "Paragraph 1 has enough text to fill the first chunk comfortably and describe the RAG retrieval architecture in complete detail.\n\n"
            "Paragraph 2 has another distinct block of content describing dense embeddings and sparse BM25 indexing techniques.\n\n"
            "Paragraph 3 contains grounded citations and faithfulness evaluation metrics."
        ),
        "collection": "default",
        "chunk_size": 150,
        "chunk_overlap": 30,
    }
    ingest_resp = client.post("/api/documents/ingest", json=payload, headers=operator_headers)
    doc_id = ingest_resp.json()["id"]

    # List documents
    list_resp = client.get("/api/documents?collection=default", headers=viewer_headers)
    assert list_resp.status_code == 200
    docs = list_resp.json()["items"]
    assert any(d["id"] == doc_id for d in docs)

    # Get chunks
    chunks_resp = client.get(f"/api/documents/{doc_id}/chunks", headers=viewer_headers)
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()["items"]
    assert len(chunks) >= 2


def test_delete_document_cascade(client, operator_headers, viewer_headers):
    payload = {
        "name": "to-delete.md",
        "text": "Temporary document text for deletion test.",
        "collection": "default",
    }
    ingest_resp = client.post("/api/documents/ingest", json=payload, headers=operator_headers)
    doc_id = ingest_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/documents/{doc_id}", headers=operator_headers)
    assert del_resp.status_code == 204

    # Verify chunks are gone
    chunks_resp = client.get(f"/api/documents/{doc_id}/chunks", headers=viewer_headers)
    assert chunks_resp.status_code == 404


def test_hybrid_search_api(client, operator_headers, viewer_headers):
    # Ingest document
    payload = {
        "name": "search-sample.md",
        "text": "PostgreSQL relational database versus SQLite in-memory storage.",
        "collection": "search-coll",
    }
    client.post("/api/documents/ingest", json=payload, headers=operator_headers)

    # Search
    search_payload = {
        "query": "SQLite in-memory",
        "collection": "search-coll",
        "top_k": 3,
        "dense_weight": 0.5,
        "sparse_weight": 0.5,
    }
    search_resp = client.post("/api/search", json=search_payload, headers=viewer_headers)
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    assert len(results) >= 1
    assert "SQLite" in results[0]["text"]
