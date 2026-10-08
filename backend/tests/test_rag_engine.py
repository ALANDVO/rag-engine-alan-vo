from app.services.rag_engine import (
    BM25Indexer,
    chunk_text,
    cosine_similarity,
    generate_deterministic_embedding,
    hybrid_search,
)


def test_chunk_text_paragraph_and_overlap():
    text = (
        "# Heading 1\n\n"
        "First substantive paragraph discussing retrieval architectures in detail.\n\n"
        "## Subheading 2\n\n"
        "Second paragraph covering dense embedding vectors and sparse BM25 indexing techniques.\n\n"
        "Third paragraph evaluating grounded citation attribution."
    )
    chunks = chunk_text(text, chunk_size=120, overlap=30)
    assert len(chunks) >= 2
    assert all("text" in c for c in chunks)
    assert all("heading" in c for c in chunks)
    assert all("content_hash" in c for c in chunks)
    assert chunks[0]["heading"] in ("Heading 1", "Subheading 2")


def test_bm25_indexer():
    chunks = [
        {"id": "c1", "text": "Python fastapi server with SQLite database storage."},
        {"id": "c2", "text": "React typescript frontend dashboard with vite bundling."},
        {"id": "c3", "text": "Keycloak OIDC authentication with PKCE verification."},
    ]
    bm25 = BM25Indexer()
    bm25.fit(chunks)

    score_c1 = bm25.score("fastapi python", "c1")
    score_c2 = bm25.score("fastapi python", "c2")
    score_c3 = bm25.score("fastapi python", "c3")

    assert score_c1 > score_c2
    assert score_c1 > score_c3


def test_deterministic_dense_embeddings():
    text1 = "Retrieval augmented generation with dense vectors."
    text2 = "Retrieval augmented generation with dense vectors."
    text3 = "Unrelated cooking recipe for apple pie dessert."

    emb1 = generate_deterministic_embedding(text1)
    emb2 = generate_deterministic_embedding(text2)
    emb3 = generate_deterministic_embedding(text3)

    assert emb1 == emb2
    assert len(emb1) == 256

    sim_identical = cosine_similarity(emb1, emb2)
    sim_different = cosine_similarity(emb1, emb3)

    assert abs(sim_identical - 1.0) < 1e-4
    assert sim_different < sim_identical


def test_hybrid_search_fusion():
    chunks = [
        {
            "id": "c1",
            "document_id": "d1",
            "document_name": "rag.md",
            "text": "Reciprocal rank fusion combines BM25 keyword rankings with dense embeddings.",
            "heading": "Fusion",
        },
        {
            "id": "c2",
            "document_id": "d2",
            "document_name": "auth.md",
            "text": "Security tokens are validated against Keycloak JWKS endpoints.",
            "heading": "Auth",
        },
    ]

    results = hybrid_search(
        query="reciprocal rank fusion BM25",
        chunks=chunks,
        dense_weight=0.5,
        sparse_weight=0.5,
        top_k=2,
    )

    assert len(results) == 2
    assert results[0]["chunk_id"] == "c1"
    assert results[0]["score"] > results[1]["score"]
