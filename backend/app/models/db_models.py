from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CollectionRecord:
    name: str
    description: str
    created_at: str
    updated_at: str


@dataclass
class DocumentRecord:
    id: str
    collection: str
    name: str
    content_type: str
    char_count: int
    chunk_count: int
    content_hash: str
    metadata_json: str
    created_at: str


@dataclass
class ChunkRecord:
    id: str
    document_id: str
    collection: str
    chunk_index: int
    text: str
    heading: str
    token_count: int
    embedding_json: str
    content_hash: str
    created_at: str


@dataclass
class GenerationRecord:
    id: str
    query: str
    answer: str
    faithfulness_score: float
    citation_precision: float
    provider: str
    model: str
    citations_json: str
    created_at: str


@dataclass
class AuditRecord:
    id: int
    timestamp: str
    action: str
    user_id: str
    user_role: str
    resource_id: str
    details: str


@dataclass
class EvaluationRecord:
    id: str
    dataset_name: str
    sample_count: int
    mrr: float
    hit_rate_1: float
    hit_rate_3: float
    hit_rate_5: float
    precision_k: float
    avg_faithfulness: float
    metrics_json: str
    created_at: str
