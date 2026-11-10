import json
import math
import time
from typing import Any, Dict, List


def calculate_ndcg_at_k(relevance_scores: List[float], k: int) -> float:
    """
    Calculate NDCG@K (Normalized Discounted Cumulative Gain at K).

    Args:
        relevance_scores: List of relevance scores for ranked items (higher = more relevant)
        k: Cutoff rank for NDCG calculation

    Returns:
        NDCG@K score in range [0.0, 1.0]
    """
    if not relevance_scores or k <= 0:
        return 0.0

    # DCG: Discounted Cumulative Gain
    dcg = sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevance_scores[:k]))

    # IDCG: Ideal DCG - sort relevance scores descending and compute DCG
    ideal_scores = sorted(relevance_scores, reverse=True)
    idcg = sum(rel / math.log2(idx + 2) for idx, rel in enumerate(ideal_scores[:k]))

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# Curated benchmark dataset with reference corpus and labeled query-target pairs
BENCHMARK_CORPUS = [
    {
        "doc_id": "doc-arch-01",
        "name": "architecture-overview.md",
        "text": """# RAG System Architecture Overview

The RAG engine uses a hybrid retrieval architecture combining sparse BM25 indexing with dense vector embeddings. Documents are ingested, chunked at paragraph boundaries with configurable overlap, and embedded using a deterministic 256-dimensional hashing scheme.

## Retrieval Pipeline

1. **Sparse Retrieval (BM25)**: Tokenizes query and documents, computes TF-IDF weighted term frequencies with BM25 scoring function. Handles exact keyword matches and partial term overlap.

2. **Dense Retrieval**: Uses deterministic SHA-256 based embedding projection to 256 dimensions. Cosine similarity provides semantic matching capability even without trained models.

3. **Reciprocal Rank Fusion (RRF)**: Combines sparse and dense rankings using RRF with configurable weights. Formula: score = w_dense * (1 / (rank_dense + k)) + w_sparse * (1 / (rank_sparse + k)) where k=60.

4. **Reranking**: Top candidates re-ranked by combined hybrid score for final output.

## Configuration

- Chunk size: 800 characters (configurable 100-4000)
- Chunk overlap: 150 characters (configurable 0-1000)
- Embedding dimension: 256 (fixed)
- Default dense_weight: 0.5, sparse_weight: 0.5
- RRF constant k: 60

## Scalability

Stateless design enables horizontal scaling. SQLite with WAL mode provides concurrent read access. Embedding computation is CPU-bound and deterministic.""",
    },
    {
        "doc_id": "doc-sec-02",
        "name": "security-architecture.md",
        "text": """# Security Architecture: Keycloak OIDC with PKCE

Authentication uses Keycloak as the OIDC provider with PKCE (Proof Key for Code Exchange) for public clients. The system enforces role-based access control with three role levels.

## Role Hierarchy

1. **Viewer** (lowest): Read-only access to documents, search, and evaluation history
2. **Operator** (middle): Can ingest documents, run evaluations, trigger generation
3. **Administrator** (highest): Full access including audit logs, system stats, user management

## PKCE Flow

- Client generates code_verifier (43-128 chars, URL-safe base64)
- code_challenge = SHA256(code_verifier) base64url-encoded
- Authorization request includes code_challenge and code_challenge_method=S256
- Token exchange validates code_verifier against stored challenge

## Demo Mode

Localhost-only HS256 JWT issuance for development. Refused when ENVIRONMENT=production. Tokens bound to 127.0.0.1 origin with short expiry.

## Credential Handling

No secrets in code. LLM_API_KEY via environment. Error messages redact sensitive values.""",
    },
    {
        "doc_id": "doc-eval-03",
        "name": "evaluation-metrics.md",
        "text": """# Evaluation Metrics: Retrieval Quality and Hallucination Prevention

The benchmark suite measures retrieval accuracy and generation faithfulness using standard IR metrics.

## Retrieval Metrics

- **MRR (Mean Reciprocal Rank)**: Average of 1/rank for first relevant document across queries
- **Hit Rate @ K**: Fraction of queries where relevant document appears in top K results
- **Precision @ K**: Fraction of top K results that are relevant
- **NDCG @ K**: Normalized Discounted Cumulative Gain - accounts for ranking position of relevant items

## Faithfulness Metrics

- **Citation Precision**: Fraction of inline citations that map to actual source chunks
- **Token Overlap**: Jaccard similarity between answer tokens and cited source tokens
- **Faithfulness Score**: Weighted combination (0.0-1.0) flagging hallucinated claims

## Benchmark Dataset

4 curated queries with gold-standard document associations covering architecture, security, evaluation, and infrastructure domains.""",
    },
    {
        "doc_id": "doc-infra-04",
        "name": "deployment-infrastructure.md",
        "text": """# Deployment Infrastructure: SQLite Persistence and Container Orchestration

Production deployment uses containerized services with persistent volumes.

## Storage Engine

- **SQLite** with WAL (Write-Ahead Logging) journal mode for concurrent access
- Parameterized queries prevent injection
- Transactional mutations with rollback on error
- Connection pooling with shared in-memory mode for tests

## Container Architecture

- Backend: FastAPI on Uvicorn, non-root user, healthcheck endpoint
- Frontend: React 18 + Vite, multi-stage nginx build, non-root user
- Keycloak: OIDC provider with realm import
- Docker Compose orchestrates all services on 127.0.0.1

## CI/CD

GitHub Actions workflow runs pytest (backend), Vitest (frontend), typecheck, and Docker builds on push to main.""",
    },
]

BENCHMARK_QUERIES = [
    {
        "query": "How does reciprocal rank fusion combine sparse and dense retrieval?",
        "expected_doc": "doc-arch-01",
        "expected_keywords": ["reciprocal", "sparse", "dense", "fusion"],
    },
    {
        "query": "What are the three role levels in the Keycloak authentication architecture?",
        "expected_doc": "doc-sec-02",
        "expected_keywords": ["viewer", "operator", "administrator", "roles"],
    },
    {
        "query": "Which metrics evaluate retrieval quality and hallucination prevention?",
        "expected_doc": "doc-eval-03",
        "expected_keywords": ["mrr", "faithfulness", "hallucination", "precision"],
    },
    {
        "query": "What storage engine and logging mode are used for persistent mutations?",
        "expected_doc": "doc-infra-04",
        "expected_keywords": ["sqlite", "wal", "transactional", "mutations"],
    },
]


def prepare_benchmark_chunks() -> List[Dict[str, Any]]:
    from app.services.rag_engine import chunk_text

    chunks: List[Dict[str, Any]] = []
    for doc in BENCHMARK_CORPUS:
        doc_chunks = chunk_text(doc["text"], chunk_size=400, overlap=50)
        for i, chunk in enumerate(doc_chunks):
            chunks.append({
                "id": f"{doc['doc_id']}-chunk-{i}",
                "document_id": doc["doc_id"],
                "document_name": doc["name"],
                "text": chunk["text"],
                "heading": "",
                "rank": 0,
            })
    return chunks


def run_evaluation(top_k: int = 3) -> Dict[str, Any]:
    from app.services.rag_engine import hybrid_search
    from app.services.citation_service import verify_grounded_citations

    chunks = prepare_benchmark_chunks()
    reciprocal_ranks = []
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    precisions = []
    faithfulness_scores = []
    ndcg_scores = []
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

        # NDCG@K calculation using reusable function
        relevance_scores = [1.0 if r["document_id"] == expected_doc else 0.0 for r in results[:top_k]]
        ndcg = calculate_ndcg_at_k(relevance_scores, top_k)
        ndcg_scores.append(ndcg)

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
            "ndcg_at_k": ndcg,
        })

    total_samples = len(BENCHMARK_QUERIES)
    mrr = sum(reciprocal_ranks) / total_samples if total_samples > 0 else 0.0
    avg_precision = sum(precisions) / total_samples if total_samples > 0 else 0.0
    avg_faithfulness = sum(faithfulness_scores) / total_samples if total_samples > 0 else 0.0
    avg_ndcg = sum(ndcg_scores) / total_samples if total_samples > 0 else 0.0

    metrics = {
        "mrr": round(mrr, 4),
        "hit_rate_1": round(hits_at_1 / total_samples, 4),
        "hit_rate_3": round(hits_at_3 / total_samples, 4),
        "hit_rate_5": round(hits_at_5 / total_samples, 4),
        "precision_k": round(avg_precision, 4),
        "avg_faithfulness": round(avg_faithfulness, 4),
        "ndcg_at_k": round(avg_ndcg, 4),
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

