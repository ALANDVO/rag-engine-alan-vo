#!/usr/bin/env python3
"""CLI interface for rag-engine preserving standalone operational workflows."""
import argparse
import json
import os
import sys

# Ensure backend modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from app.core.database import get_db, init_db, utc_now
from app.services.citation_service import verify_grounded_citations
from app.services.llm_service import llm_service
from app.services.rag_engine import (
    chunk_text,
    compute_hash,
    generate_deterministic_embedding,
    hybrid_search,
)


def ingest_cli(args):
    init_db()
    path = args.path
    files = []
    if os.path.isdir(path):
        for root, _, names in os.walk(path):
            files.extend(
                os.path.join(root, n)
                for n in names
                if n.lower().endswith((".md", ".txt", ".py", ".js", ".json", ".yaml", ".yml"))
            )
    elif os.path.exists(path):
        files = [path]
    else:
        print(f"Path not found: {path}")
        return

    print(f"Ingesting {len(files)} file(s) into collection '{args.name}'...")
    now = utc_now()

    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO collections (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (args.name, f"CLI collection {args.name}", now, now),
        )

        total_chunks = 0
        for filepath in files:
            with open(filepath, "r", errors="replace") as f:
                content = f.read()

            chunks = chunk_text(content)
            if not chunks:
                continue

            doc_id = f"cli-{compute_hash(filepath)[:10]}"
            conn.execute(
                "INSERT OR REPLACE INTO documents (id, collection, name, content_type, char_count, chunk_count, content_hash, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, args.name, os.path.basename(filepath), "text/plain", len(content), len(chunks), compute_hash(content), "{}", now),
            )

            for i, c in enumerate(chunks):
                cid = f"{doc_id}_c{i}"
                emb = generate_deterministic_embedding(c["text"])
                conn.execute(
                    "INSERT OR REPLACE INTO chunks (id, document_id, collection, chunk_index, text, heading, token_count, embedding_json, content_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (cid, doc_id, args.name, i, c["text"], c["heading"], c["token_count"], json.dumps(emb), c["content_hash"], now),
                )
            total_chunks += len(chunks)

    print(f"Collection '{args.name}': {total_chunks} chunks indexed successfully.")


def search_cli(args):
    init_db()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT c.id, c.document_id, c.text, c.heading, c.embedding_json, d.name as document_name FROM chunks c JOIN documents d ON c.document_id = d.id WHERE c.collection = ?",
            (args.collection,),
        ).fetchall()

    chunks = [
        {"id": r["id"], "document_id": r["document_id"], "document_name": r["document_name"], "text": r["text"], "heading": r["heading"], "embedding": r["embedding_json"]}
        for r in rows
    ]

    results = hybrid_search(args.query, chunks, top_k=args.top)
    print(f"Top {len(results)} results for query: '{args.query}'\n")
    for r in results:
        print(f"[{r['rank']}] Score: {r['score']:.4f} (Dense: {r['dense_score']:.4f}, Sparse: {r['sparse_score']:.4f})")
        print(f"    Source: {r['document_name']} | Heading: {r['heading']}")
        print(f"    {r['text'][:200]}...\n")


def generate_cli(args):
    import asyncio
    init_db()

    async def _run():
        with get_db() as conn:
            rows = conn.execute(
                "SELECT c.id, c.document_id, c.text, c.heading, c.embedding_json, d.name as document_name FROM chunks c JOIN documents d ON c.document_id = d.id WHERE c.collection = ?",
                (args.collection,),
            ).fetchall()

        chunks = [
            {"id": r["id"], "document_id": r["document_id"], "document_name": r["document_name"], "text": r["text"], "heading": r["heading"], "embedding": r["embedding_json"]}
            for r in rows
        ]

        retrieved = hybrid_search(args.question, chunks, top_k=args.context)
        out = await llm_service.generate_response(args.question, context_chunks=retrieved)
        citations, faith = verify_grounded_citations(out["answer"], retrieved)

        print("=" * 60)
        print("GROUNDED ANSWER")
        print("=" * 60)
        print(out["answer"])
        print(f"\nGrounding Score: {faith['faithfulness_score'] * 100:.1f}% ({faith['summary']})")
        print("\nCITATIONS:")
        for c in citations:
            status_lbl = "Verified" if c["verified"] else "Ungrounded"
            print(f"  [{c['index']}] {c['document_name']} ({status_lbl}) - {c['snippet'][:100]}...")

    asyncio.run(_run())


def main():
    p = argparse.ArgumentParser(prog="rag-engine", description="RAG engine CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("ingest")
    i.add_argument("path")
    i.add_argument("--name", default="default")
    i.set_defaults(fn=ingest_cli)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--collection", default="default")
    s.add_argument("--top", type=int, default=5)
    s.set_defaults(fn=search_cli)

    g = sub.add_parser("generate")
    g.add_argument("question")
    g.add_argument("--collection", default="default")
    g.add_argument("--context", type=int, default=4)
    g.set_defaults(fn=generate_cli)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
