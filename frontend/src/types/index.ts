export type UserRole = "viewer" | "operator" | "admin";

export interface UserSession {
  user_id: string;
  username: string;
  roles: string[];
  effective_role: UserRole;
  is_demo: boolean;
}

export interface DocumentItem {
  id: string;
  collection: string;
  name: string;
  content_type: string;
  char_count: number;
  chunk_count: number;
  content_hash: string;
  created_at: string;
}

export interface ChunkItem {
  id: string;
  document_id: string;
  collection: string;
  chunk_index: number;
  text: string;
  heading: string;
  token_count: number;
  created_at: string;
}

export interface SearchResultItem {
  rank: number;
  chunk_id: string;
  document_id: string;
  document_name: string;
  score: number;
  dense_score: number;
  sparse_score: number;
  text: string;
  heading: string;
}

export interface SearchResponse {
  query: string;
  collection: string;
  total_results: number;
  results: SearchResultItem[];
  search_time_ms: number;
}

export interface CitationItem {
  index: number;
  chunk_id: string;
  document_name: string;
  snippet: string;
  verified: boolean;
  overlap_score: number;
}

export interface FaithfulnessMetrics {
  faithfulness_score: number;
  citation_precision: number;
  verified_claims_count: number;
  total_citations_count: number;
  advisory: boolean;
  summary: string;
}

export interface GenerateResponse {
  question: string;
  answer: string;
  citations: CitationItem[];
  faithfulness: FaithfulnessMetrics;
  provider: string;
  model: string;
  execution_time_ms: number;
}

export interface EvaluationMetrics {
  mrr: number;
  hit_rate_1: number;
  hit_rate_3: number;
  hit_rate_5: number;
  precision_k: number;
  avg_faithfulness: number;
  total_samples: number;
  elapsed_ms: number;
}

export interface EvaluationResult {
  id: string;
  dataset_name: string;
  metrics: EvaluationMetrics;
  sample_details: Array<{
    query: string;
    target_doc: string;
    retrieved_top: string;
    first_rank: number;
    score: number;
    faithfulness: number;
  }>;
  run_at: string;
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  action: string;
  user_id: string;
  user_role: string;
  resource_id: string;
  details: string;
}

export interface StatsResponse {
  total_documents: number;
  total_chunks: number;
  total_collections: number;
  total_generations: number;
  avg_faithfulness: number;
}
