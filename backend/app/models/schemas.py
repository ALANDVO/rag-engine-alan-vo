from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Health & Config
class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    demo_mode: bool
    llm_provider: str
    llm_configured: bool


class OIDCConfigResponse(BaseModel):
    client_id: str
    issuer_url: str
    audience: str
    demo_mode: bool


# Auth Schemas
class TokenExchangeRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    roles: List[str]


class UserSession(BaseModel):
    user_id: str
    username: str
    roles: List[str]
    effective_role: str
    is_demo: bool


class DemoLoginRequest(BaseModel):
    role: str = Field(default="operator", pattern="^(viewer|operator|admin)$")
    username: str = "demo-user"


# Document Schemas
class DocumentCreate(BaseModel):
    collection: str = Field(default="default", min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1)
    chunk_size: int = Field(default=800, ge=100, le=4000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    id: str
    collection: str
    name: str
    content_type: str
    char_count: int
    chunk_count: int
    content_hash: str
    created_at: str


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    collection: str
    chunk_index: int
    text: str
    heading: str
    token_count: int
    created_at: str


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    size: int


class ChunkListResponse(BaseModel):
    items: List[ChunkResponse]
    total: int


# Search Schemas
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    collection: str = Field(default="default", max_length=64)
    top_k: int = Field(default=5, ge=1, le=50)
    dense_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    sparse_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    document_name: str
    score: float
    dense_score: float
    sparse_score: float
    text: str
    heading: str


class SearchResponse(BaseModel):
    query: str
    collection: str
    total_results: int
    results: List[SearchResultItem]
    search_time_ms: float


# Grounded Generation & Citations
class GenerateRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    collection: str = Field(default="default", max_length=64)
    top_k: int = Field(default=4, ge=1, le=10)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


class CitationItem(BaseModel):
    index: int
    chunk_id: str
    document_name: str
    snippet: str
    verified: bool
    overlap_score: float


class FaithfulnessMetrics(BaseModel):
    faithfulness_score: float
    citation_precision: float
    verified_claims_count: int
    total_citations_count: int
    advisory: bool = True
    summary: str


class GenerateResponse(BaseModel):
    question: str
    answer: str
    citations: List[CitationItem]
    faithfulness: FaithfulnessMetrics
    provider: str
    model: str
    execution_time_ms: float


# Evaluation Schemas
class EvaluationRunRequest(BaseModel):
    dataset_name: str = "rag-benchmark-v1"
    top_k: int = Field(default=3, ge=1, le=10)


class EvaluationMetricSummary(BaseModel):
    mrr: float
    hit_rate_1: float
    hit_rate_3: float
    hit_rate_5: float
    precision_k: float
    avg_faithfulness: float
    total_samples: int


class EvaluationResultResponse(BaseModel):
    id: str
    dataset_name: str
    metrics: EvaluationMetricSummary
    sample_details: List[Dict[str, Any]]
    run_at: str


# Audit & Stats
class AuditLogEntry(BaseModel):
    id: int
    timestamp: str
    action: str
    user_id: str
    user_role: str
    resource_id: str
    details: str


class AuditLogResponse(BaseModel):
    entries: List[AuditLogEntry]
    total: int
    page: int
    size: int


class StatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_collections: int
    total_generations: int
    avg_faithfulness: float
