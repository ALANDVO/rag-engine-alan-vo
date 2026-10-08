import json
import time
from typing import Any, Dict, List, Tuple
from app.services.rag_engine import hybrid_search, chunk_text
from app.services.citation_service import verify_grounded_citations


# Curated benchmark dataset with reference corpus and labeled query-target pairs
BENCHMARK_CORPUS = [
    {
        "id": "doc-arch-01",
        "name": "architecture-overview.md",
        "text": """# System Architecture Overview
The RAG engine decouples retrieval indexing from generation adapters.
All document chunks are indexed using dual sparse BM25 representations and deterministic 256-dimensional dense feature vectors.
Reciprocal Rank Fusion fuses both ranking spaces to maximize recall across lexical keywords and semantic paraphrasing."""
    },
    {
        "id": "doc-sec-02",
        "name": "security-authentication.md",
        "text": """# Authentication and OIDC Specification
Authentication utilizes OpenID Connect (OIDC) through Keycloak identity brokering with PKCE and state/nonce verification.
Role-based access control enforces three distinct roles: viewer, operator, and administrator.
Demo mode strictly binds to localhost and is rejected on production startup."""
    },
    {
        "id": "doc-eval-03",
        "name": "evaluation-metrics.md",
        "text": """# Retrieval and Grounding Evaluation
Retrieval benchmarks evaluate Mean Reciprocal Rank (MRR), Hit Rate@K, and Precision@K over gold standard query sets.
Answer generation evaluates faithfulness and hallucination using token overlap verification between citations and source text.
Deterministic offline execution ensures evaluation pipelines run without network dependency."""
    },
    {
        "id": "doc-infra-04",
        "name": "deployment-infrastructure.md",
        "text": """# Container Deployment and Storage
Backend and frontend services deploy as non-root containers with Alpine base images and healthcheck probes.
SQLite database storage runs with Write-Ahead Logging (WAL) and transactional mutations for local persistence.
Audit logs record every document mutation, query execution, and role elevation."""
    }
]

BENCHMARK_QUERIES = [
    {
        "query": "How does reciprocal rank fusion combine sparse and dense retrieval?",
        "expected_doc": "doc-arch-01",
        "expected_keywords": ["reciprocal", "sparse", "dense", "fusion"]
    },
    {
        "query": "What are the three role levels in the Keycloak authentication architecture?",
        "expected_doc": "doc-sec-02",
        "expected_keywords": ["viewer", "operator", "administrator", "roles"]
    },
    {
        "query": "Which metrics evaluate retrieval quality and hallucination prevention?",
        "expected_doc": "doc-eval-03",
        "expected_keywords": ["mrr", "faithfulness", "hallucination", "precision"]
    },
    {
        "query": "What storage engine and logging mode are used for persistent mutations?",
        "expected_doc": "doc-infra-04",
        "expected_keywords": ["sqlite", "wal", "transactional", "mutations"]
    }
]


def prepare_benchmark_chunks() -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for doc in BENCHMARK_CORPUS:
        doc_chunks = chunk_text(doc["text"], chunk_size=400, overlap=50)
        for i, c in enumerate(doc_chunks):
            cid = f"{doc['id']}_chunk_{i}"
            chunks.append({
                "id": cid,
                "document_id": doc["id"],
                "document_name": doc["name"],
                "text": c["text"],
                "heading": c["heading"],
                "embedding": []
            })
    return chunks


def run_evaluation(top_k: int = 3) -> Dict[str, Any]:
    chunks = prepare_benchmark_chunks()
    reciprocal_ranks = []
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    precisions = []
    faithfulness_scores = []
    sample_details = []

    start_time = time.time()

    for item in BENCHMARK_QUERIES:
        q = item["query"]
        expected_doc = item["expected_doc"]

        results = hybrid_search(q, chunks, dense_weight=0.5, sparse_weight=0.5, top_k=5)

        # Calculate rank of first relevant chunk
        found_rank = None
        for r in results:
            if r["document_id"] == expected_doc:
                found_rank = r["rank"]
                break

        if found_rank:
            reciprocal_ranks.append(1.0 / found_rank)
            if found_rank == 1:
                hits_at_1 += 1
            if found_rank <= 3:
                hits_at_3 += 1
            if found_rank <= 5:
                hits_at_5 += 1
        else:
            reciprocal_ranks.append(0.0)

        # Precision at K
        relevant_in_top = sum(1 for r in results[:top_k] if r["document_id"] == expected_doc)
        precision_k = relevant_in_top / top_k
        precisions.append(precision_k)

        # Mock generated response with citation for faithfulness check
        simulated_answer = f"According to the system documentation, {results[0]['text'][:100]} [1]." if results else "No context."
        _, faith_metrics = verify_grounded_citations(simulated_answer, results[:1])
        faithfulness_scores.append(faith_metrics["faithfulness_score"])

        sample_details.append({
            "query": q,
            "target_doc": expected_doc,
            "retrieved_top": results[0]["document_name"] if results else "none",
            "first_rank": found_rank or 0,
            "score": results[0]["score"] if results else 0.0,
            "faithfulness": faith_metrics["faithfulness_score"],
        })

    total_samples = len(BENCHMARK_QUERIES)
    mrr = sum(reciprocal_ranks) / total_samples if total_samples > 0 else 0.0
    avg_precision = sum(precisions) / total_samples if total_samples > 0 else 0.0
    avg_faithfulness = sum(faithfulness_scores) / total_samples if total_samples > 0 else 0.0

    metrics = {
        "mrr": round(mrr, 4),
        "hit_rate_1": round(hits_at_1 / total_samples, 4),
        "hit_rate_3": round(hits_at_3 / total_samples, 4),
        "hit_rate_5": round(hits_at_5 / total_samples, 4),
        "precision_k": round(avg_precision, 4),
        "avg_faithfulness": round(avg_faithfulness, 4),
        "total_samples": total_samples,
        "elapsed_ms": round((time.time() - start_time) * 1000, 2),
    }

    return {
        "dataset_name": "rag-benchmark-v1",
        "metrics": metrics,
        "sample_details": sample_details,
    }


if __name__ == "__main__":
    res = run_evaluation()
    print("=== RAG Evaluation Benchmark Results ===")
    print(json.dumps(res, indent=2))
