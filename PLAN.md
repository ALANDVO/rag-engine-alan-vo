# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

remove-obsolete-root-artifacts

## Roadmap

### document-ingestion — Multi-format document ingestion with chunking and embedding

Status: done

Acceptance:
- Ingest Markdown/TXT/JSON/code files via POST /api/documents/ingest (operator role)
- Paragraph-boundary chunking with configurable size and overlap produces >=1 chunks
- Each chunk stores a deterministic 256-dim embedding and SHA-256 content hash
- Documents list with pagination at GET /api/documents
- Chunk details and full content reconstruction endpoints

Implementation: `backend/app/api/documents.py`, `backend/app/services/rag_engine.py`

Tests: `backend/tests/test_documents_and_search.py`

### hybrid-retrieval — Hybrid BM25 + dense cosine retrieval with RRF reranking

Status: done

Acceptance:
- POST /api/search returns ranked chunks with score, dense_score, sparse_score
- BM25 sparse scoring ranked above unrelated documents for keyword queries
- Deterministic 256-dim embeddings produce cosine similarity > 0.8 for identical text
- Configurable dense_weight and sparse_weight parameters

Implementation: `backend/app/services/rag_engine.py`, `backend/app/api/search.py`

Tests: `backend/tests/test_rag_engine.py`, `backend/tests/test_documents_and_search.py`

### citation-verification — Deterministic citation attribution and faithfulness scoring

Status: done

Acceptance:
- Inline [n] citations parsed from answers and mapped to source chunks
- Token-overlap verification produces verified=True for grounded claims
- Faithfulness score (0.0-1.0) flags hallucinated claims
- POST /api/generate returns citations with overlap scores and metrics

Implementation: `backend/app/services/citation_service.py`, `backend/app/api/generate.py`

Tests: `backend/tests/test_citation_service.py`

### llm-adapters — Multi-provider LLM adapters with offline fallback

Status: done

Acceptance:
- OpenAI-compatible, Anthropic, Gemini, and Ollama adapters via httpx
- Deterministic offline synthesizer when no LLM_API_KEY configured
- Credential redaction in error messages; bounded timeouts

Implementation: `backend/app/services/llm_service.py`

Tests: `backend/tests/test_llm_service.py`

### auth-oidc — Keycloak OIDC with PKCE, roles, and local demo mode

Status: done

Acceptance:
- Demo mode issues HS256 bearer tokens bound to localhost
- Role-based authorization: viewer/operator/admin enforced on all endpoints
- Unauthenticated requests rejected with 401
- PKCE code_verifier length validated (43-128 chars) at /api/auth/token
- Demo mode refused when ENVIRONMENT=production

Implementation: `backend/app/core/security.py`, `backend/app/api/auth.py`, `keycloak/realm-export.json`

Tests: `backend/tests/test_auth.py`, `backend/tests/test_http_boundary.py`

### evaluation-benchmark — AI/ML evaluation benchmark with MRR, Hit@K, Precision@K

Status: done

Acceptance:
- run_evaluation() computes MRR, Hit@K, Precision@K, and faithfulness over 4-query benchmark
- POST /api/evaluation/run records metrics to SQLite
- GET /api/evaluation/history returns past runs
- Results exposed in frontend EvaluationDashboard

Implementation: `backend/app/services/evaluation_service.py`, `backend/app/api/evaluation.py`

Tests: `backend/tests/test_evaluation_benchmark.py`

### audit-telemetry — Audit logging and system telemetry

Status: done

Acceptance:
- Every document mutation, search, and eval run logged to audit_logs table
- GET /api/audit (admin) returns paginated audit entries
- GET /api/stats returns document/chunk/generation counts and avg faithfulness
- Frontend AuditLogView renders stats grid and audit table

Implementation: `backend/app/services/audit_service.py`, `backend/app/api/audit.py`

Tests: `backend/tests/test_auth.py`

### fullstack-ui — React + TypeScript dashboard with domain workflows

Status: done

Acceptance:
- Document Ingestion, Search Workbench, Grounded QA, Evaluation, and Audit views
- Typed API client matching backend response envelopes
- Loading, error, and empty states on all workflows
- Vite production build and Vitest tests pass

Implementation: `frontend/src/App.tsx`, `frontend/src/components/`, `frontend/src/api/client.ts`, `frontend/src/types/index.ts`

Tests: `frontend/src/test/App.test.tsx`, `frontend/src/test/GroundedQA.test.tsx`, `frontend/src/test/SearchWorkbench.test.tsx`

### container-deploy — Production containers, compose, and CI

Status: done

Acceptance:
- backend/Dockerfile runs as non-root user with healthcheck
- frontend/Dockerfile builds via multi-stage nginx with non-root user
- compose.yaml launches Keycloak, backend, and frontend on 127.0.0.1
- CI workflow builds both images and runs all tests

Implementation: `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml`

### remove-obsolete-root-artifacts — Remove obsolete root-level deployment artifacts and fix references

Status: done

Acceptance:
- Root Dockerfile (broken uvicorn main:app), root requirements.txt, docker-compose.yml, and llm_client.py removed
- CONTRIBUTING.md setup path corrected to backend/requirements.txt
- Preflight passes with no missing required files

Implementation: `CONTRIBUTING.md`

