# Changelog

All notable changes to `rag-engine-alan-vo` will be documented in this file.

## [1.0.0] - 2026-10-08

### Added
- Complete full-stack baseline layout complying with the owned-app production contract.
- Modular FastAPI backend with persistent SQLite storage, parameterized queries, and transactional mutations.
- Multi-format document ingestion engine supporting Markdown, TXT, JSON, code, and PDF files.
- Deterministic semantic chunking engine with configurable chunk sizes, paragraph-boundary preservation, and sliding overlap.
- Deterministic hybrid retrieval system combining sparse BM25 indexing and dense vector cosine similarity with Reciprocal Rank Fusion (RRF).
- Grounded citation attribution engine parsing and validating inline `[n]` references against retrieved source context chunks.
- Automated faithfulness and hallucination evaluation scoring based on token overlap and n-gram alignment.
- Multi-provider LLM adapter supporting OpenAI-compatible APIs, Anthropic messages, Gemini generateContent, and local Ollama instances.
- Comprehensive AI/ML evaluation benchmark suite reporting Precision@K, Recall@K, MRR (Mean Reciprocal Rank), Hit Rate@K, and faithfulness metrics.
- Secure Keycloak OIDC authentication architecture with PKCE code challenge verification, strict role-based authorization (`viewer`, `operator`, `admin`), and localhost-only demo mode.
- Keycloak realm configuration export with SAML identity brokering architecture.
- Full React 18 + TypeScript + Vite frontend dashboard with interactive Document Ingestion, Hybrid Search Workbench, Grounded Q&A with clickable citation pills, AI/ML Evaluation Dashboard, and Audit Log Viewer.
- Production Dockerfiles for backend and frontend with non-root security boundaries, plus root compose.yaml with Keycloak and SQLite persistent volumes.
- CI workflow running automated backend pytest suite, frontend Vitest tests, and Docker container builds.
