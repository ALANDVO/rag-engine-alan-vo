from app.services.citation_service import (
    parse_inline_citations,
    verify_grounded_citations,
)


def test_parse_inline_citations():
    text = "The system uses BM25 [1] and reciprocal rank fusion [2], alongside Keycloak [1]."
    citations = parse_inline_citations(text)
    assert citations == [1, 2]


def test_citation_verification_grounded():
    context = [
        {
            "id": "c1",
            "document_name": "rag.md",
            "text": "Reciprocal rank fusion fuses dense cosine similarity with sparse BM25 scores.",
        },
        {
            "id": "c2",
            "document_name": "sec.md",
            "text": "Authentication uses OpenID Connect with PKCE authorization codes.",
        },
    ]

    answer = (
        "Reciprocal rank fusion fuses dense cosine similarity with sparse BM25 scores [1]. "
        "Authentication uses OpenID Connect with PKCE authorization codes [2]."
    )

    items, metrics = verify_grounded_citations(answer, context)

    assert len(items) == 2
    assert items[0]["verified"] is True
    assert items[1]["verified"] is True
    assert metrics["faithfulness_score"] >= 0.8
    assert metrics["verified_claims_count"] == 2


def test_citation_verification_hallucination():
    context = [
        {
            "id": "c1",
            "document_name": "rag.md",
            "text": "The engine stores documents in local SQLite tables.",
        }
    ]

    # Citing an index that does not exist in context (e.g. [5])
    answer = "The system automatically launches autonomous quantum rockets [5]."
    items, metrics = verify_grounded_citations(answer, context)

    assert len(items) == 1
    assert items[0]["verified"] is False
    assert metrics["faithfulness_score"] == 0.0
