import re
from typing import Any, Dict, List, Tuple
from app.services.rag_engine import tokenize


def parse_inline_citations(text: str) -> List[int]:
    matches = re.findall(r"\[(\d+)\]", text)
    citations = []
    for m in matches:
        try:
            val = int(m)
            if val not in citations:
                citations.append(val)
        except ValueError:
            pass
    return sorted(citations)


def calculate_overlap_score(claim_tokens: List[str], chunk_tokens: List[str]) -> float:
    if not claim_tokens or not chunk_tokens:
        return 0.0
    claim_set = set(claim_tokens)
    chunk_set = set(chunk_tokens)
    overlap = claim_set.intersection(chunk_set)
    return len(overlap) / len(claim_set)


def verify_grounded_citations(
    answer: str,
    context_chunks: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    citation_indices = parse_inline_citations(answer)
    citation_items: List[Dict[str, Any]] = []

    # Break answer into sentences
    sentences = re.split(r"(?<=[.!?])\s+", answer)
    total_claims = 0
    verified_claims = 0

    for idx in citation_indices:
        chunk_idx = idx - 1
        if 0 <= chunk_idx < len(context_chunks):
            chunk = context_chunks[chunk_idx]
            chunk_text = chunk.get("text", "")
            chunk_tokens = tokenize(chunk_text)

            # Find sentences referencing this citation
            matching_sentences = []
            for i, s in enumerate(sentences):
                if f"[{idx}]" in s:
                    s_tokens = tokenize(re.sub(r"\[\d+\]", "", s))
                    if len(s_tokens) < 3 and i > 0:
                        matching_sentences.append(sentences[i - 1] + " " + s)
                    else:
                        matching_sentences.append(s)

            if not matching_sentences:
                matching_sentences = [answer]

            claim_tokens = []
            for s in matching_sentences:
                clean_s = re.sub(r"\[\d+\]", "", s)
                claim_tokens.extend(tokenize(clean_s))

            overlap = calculate_overlap_score(claim_tokens, chunk_tokens)
            is_verified = overlap >= 0.20 or len(chunk_tokens) < 10

            total_claims += 1
            if is_verified:
                verified_claims += 1

            snippet = chunk_text[:200] + ("..." if len(chunk_text) > 200 else "")
            citation_items.append({
                "index": idx,
                "chunk_id": chunk.get("chunk_id", chunk.get("id", f"chunk-{idx}")),
                "document_name": chunk.get("document_name", "Document"),
                "snippet": snippet,
                "verified": is_verified,
                "overlap_score": round(overlap, 4),
            })
        else:
            total_claims += 1
            citation_items.append({
                "index": idx,
                "chunk_id": "missing",
                "document_name": "Unknown",
                "snippet": "Cited source chunk not found in retrieved context.",
                "verified": False,
                "overlap_score": 0.0,
            })

    faithfulness_score = (verified_claims / total_claims) if total_claims > 0 else (1.0 if not answer else 0.5)
    citation_precision = (verified_claims / len(citation_indices)) if citation_indices else 1.0

    if faithfulness_score >= 0.8:
        summary = "High grounding: All claims trace directly to verified source context."
    elif faithfulness_score >= 0.5:
        summary = "Moderate grounding: Most claims supported by citations; review advisory flags."
    else:
        summary = "Low grounding: Detected unverified claims; potential hallucination."

    metrics = {
        "faithfulness_score": round(faithfulness_score, 4),
        "citation_precision": round(citation_precision, 4),
        "verified_claims_count": verified_claims,
        "total_citations_count": len(citation_indices),
        "advisory": True,
        "summary": summary,
    }

    return citation_items, metrics
