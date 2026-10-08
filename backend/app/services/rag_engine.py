import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> List[str]:
    clean = re.sub(r"[^\w\s-]", " ", text.lower())
    tokens = [t for t in clean.split() if len(t) > 1]
    return tokens


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150
) -> List[Dict[str, Any]]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: List[Dict[str, Any]] = []
    current_chunk = ""
    current_heading = ""

    for para in paragraphs:
        lines = para.strip().splitlines()
        for line in lines:
            if line.strip().startswith("#"):
                current_heading = line.strip().lstrip("#").strip()

        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            clean_chunk = current_chunk.strip()
            if len(clean_chunk) > 20:
                chunks.append({
                    "text": clean_chunk,
                    "heading": current_heading,
                    "token_count": len(tokenize(clean_chunk)),
                    "content_hash": compute_hash(clean_chunk),
                })
            current_chunk = current_chunk[-overlap:] if overlap < len(current_chunk) else ""

        current_chunk += para + "\n\n"

    if current_chunk.strip() and len(current_chunk.strip()) > 20:
        clean_chunk = current_chunk.strip()
        chunks.append({
            "text": clean_chunk,
            "heading": current_heading,
            "token_count": len(tokenize(clean_chunk)),
            "content_hash": compute_hash(clean_chunk),
        })

    return chunks


def generate_deterministic_embedding(text: str, dim: int = 256) -> List[float]:
    """Generates a reproducible, deterministic dense unit vector from text tokens and n-grams."""
    vec = [0.0] * dim
    tokens = tokenize(text)
    if not tokens:
        return vec

    for i, token in enumerate(tokens):
        # Word hashing
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dim
        vec[h] += 1.0

        # Character trigrams for morphological capture
        if len(token) >= 3:
            for j in range(len(token) - 2):
                tri = token[j:j+3]
                h_tri = int(hashlib.md5(tri.encode("utf-8")).hexdigest(), 16) % dim
                vec[h_tri] += 0.5

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 6) for x in vec]
    return vec


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    sim = dot / (norm1 * norm2)
    return max(0.0, min(1.0, sim))


class BM25Indexer:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_lens: Dict[str, int] = {}
        self.doc_tokens: Dict[str, List[str]] = {}
        self.df: Dict[str, int] = {}

    def fit(self, chunks: List[Dict[str, Any]]) -> None:
        self.doc_count = len(chunks)
        if self.doc_count == 0:
            return

        total_len = 0
        self.df.clear()
        self.doc_tokens.clear()
        self.doc_lens.clear()

        for chunk in chunks:
            cid = chunk["id"]
            tokens = tokenize(chunk["text"])
            self.doc_tokens[cid] = tokens
            self.doc_lens[cid] = len(tokens)
            total_len += len(tokens)

            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.df[t] = self.df.get(t, 0) + 1

        self.avg_doc_len = total_len / self.doc_count if self.doc_count > 0 else 1.0

    def score(self, query: str, chunk_id: str) -> float:
        query_tokens = tokenize(query)
        if not query_tokens or chunk_id not in self.doc_tokens:
            return 0.0

        doc_tokens = self.doc_tokens[chunk_id]
        doc_len = self.doc_lens[chunk_id]
        score = 0.0

        tf_map: Dict[str, int] = {}
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        for q in query_tokens:
            if q not in self.df:
                continue
            df = self.df[q]
            # Standard BM25 IDF
            idf = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))
            tf = tf_map.get(q, 0)
            numerator = tf * (self.k1 + 1.0)
            denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
            if denominator > 0:
                score += idf * (numerator / denominator)

        return max(0.0, score)


def hybrid_search(
    query: str,
    chunks: List[Dict[str, Any]],
    dense_weight: float = 0.5,
    sparse_weight: float = 0.5,
    top_k: int = 5,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:
    if not chunks:
        return []

    # 1. Sparse BM25
    bm25 = BM25Indexer()
    bm25.fit(chunks)
    sparse_scores: Dict[str, float] = {}
    for c in chunks:
        sparse_scores[c["id"]] = bm25.score(query, c["id"])

    max_sparse = max(sparse_scores.values()) if sparse_scores else 1.0
    if max_sparse <= 0:
        max_sparse = 1.0

    # 2. Dense Vector
    query_emb = generate_deterministic_embedding(query)
    dense_scores: Dict[str, float] = {}
    for c in chunks:
        c_emb = c.get("embedding") or []
        if isinstance(c_emb, str):
            try:
                c_emb = json.loads(c_emb)
            except Exception:
                c_emb = []
        if not c_emb:
            c_emb = generate_deterministic_embedding(c["text"])
        dense_scores[c["id"]] = cosine_similarity(query_emb, c_emb)

    # 3. Hybrid Fusion
    results: List[Dict[str, Any]] = []
    for c in chunks:
        cid = c["id"]
        norm_sparse = sparse_scores.get(cid, 0.0) / max_sparse
        norm_dense = dense_scores.get(cid, 0.0)
        combined = (dense_weight * norm_dense) + (sparse_weight * norm_sparse)

        if combined >= min_score:
            results.append({
                "chunk_id": cid,
                "document_id": c.get("document_id", ""),
                "document_name": c.get("document_name", ""),
                "score": round(combined, 4),
                "dense_score": round(norm_dense, 4),
                "sparse_score": round(norm_sparse, 4),
                "text": c["text"],
                "heading": c.get("heading", ""),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(results[:top_k], 1):
        r["rank"] = i
    return results[:top_k]
