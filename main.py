#!/usr/bin/env python3
# rag-engine — Retrieval-Augmented Generation engine that ingests documents (PDF, MD, JSON), chunks and embeds them with an API, and serves semantic search plus generation with grounded citations.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
import math

def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)

def _embed_text(llm, text):
    """Embed text using the OpenAI-compatible embeddings endpoint."""
    import requests
    headers = {"Content-Type": "application/json"}
    if llm.api_key:
        headers["Authorization"] = f"Bearer {llm.api_key}"
    payload = {"model": os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"), "input": text[:8000]}
    r = requests.post(f"{llm.base_url}/embeddings", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]

def _chunk_text(text, chunk_size=1200, overlap=200):
    """Chunk text by paragraph boundaries with overlap."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > chunk_size and current:
            chunks.append(current.strip())
            current = current[-overlap:] if overlap else ""
        current += para + "\n\n"
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 20]

def _extract_text(path):
    """Extract text from supported file formats."""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", errors="replace") as f:
        text = f.read()
    if ext in (".md", ".txt", ".py", ".js", ".go", ".rs", ".json", ".yaml", ".yml", ".toml"):
        return text
    if ext == ".pdf":
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(path)
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except ImportError:
            return text
    return text

def _collection_path(name):
    base = os.path.join(os.path.dirname(__file__), "collections")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{name}.json")

def _load_collection(name):
    path = _collection_path(name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Collection '{name}' not found. Run 'ingest' first.")
    with open(path) as f:
        return json.load(f)

def _save_collection(name, data):
    with open(_collection_path(name), "w") as f:
        json.dump(data, f)

def ingest(args):
    """Ingest documents into a named collection."""
    llm = LLM()
    path = args.path
    files = []
    if os.path.isdir(path):
        for root, _, names in os.walk(path):
            files.extend(os.path.join(root, n) for n in names if n.lower().endswith((".md", ".txt", ".py", ".js", ".go", ".rs", ".json", ".yaml", ".yml", ".toml", ".pdf")))
    elif os.path.exists(path):
        files = [path]
    else:
        print(f"Path not found: {path}")
        return

    print(f"Ingesting {len(files)} file(s) into collection '{args.name}'...")
    data = _load_collection(args.name) if os.path.exists(_collection_path(args.name)) else {"name": args.name, "chunks": [], "created": datetime.now().isoformat()}

    for filepath in files:
        text = _extract_text(filepath)
        chunks = _chunk_text(text)
        if not chunks:
            print(f"  {filepath}: no chunks (empty or binary)")
            continue
        print(f"  {filepath}: {len(chunks)} chunk(s)")
        for i, chunk in enumerate(chunks):
            try:
                embedding = _embed_text(llm, chunk)
            except Exception as e:
                print(f"    embed failed for chunk {i}: {e}")
                continue
            data["chunks"].append({
                "id": f"{os.path.basename(filepath)}:{i}",
                "source": filepath,
                "text": chunk,
                "embedding": embedding,
            })

    _save_collection(args.name, data)
    print(f"\nCollection '{args.name}': {len(data['chunks'])} chunks total")

def search(args):
    """Semantic search over a collection."""
    llm = LLM()
    data = _load_collection(args.name)
    query = args.query
    print(f"Searching '{args.name}' for: {query}\n")

    q_emb = _embed_text(llm, query)
    scored = []
    for chunk in data["chunks"]:
        sim = _cosine(q_emb, chunk["embedding"])
        scored.append((sim, chunk))
    scored.sort(key=lambda x: -x[0])

    top = scored[:args.top]
    for rank, (sim, chunk) in enumerate(top, 1):
        print(f"[{rank}] similarity={sim:.4f}  source={chunk['source']}  id={chunk['id']}")
        snippet = chunk["text"][:300].replace("\n", " ")
        print(f"    {snippet}...")
        print()

    if args.output:
        with open(args.output, "w") as f:
            json.dump([{"rank": i + 1, "similarity": round(s, 4), "source": c["source"], "text": c["text"]} for i, (s, c) in enumerate(top)], f, indent=2)
        print(f"Saved to {args.output}")
    return top

def generate(args):
    """Generate a grounded answer with citations from a collection."""
    llm = LLM()
    data = _load_collection(args.name)
    question = args.question

    q_emb = _embed_text(llm, question)
    scored = sorted([(_cosine(q_emb, c["embedding"]), c) for c in data["chunks"]], key=lambda x: -x[0])
    context_chunks = [c for _, c in scored[:args.context]]

    context = "\n\n".join(f"[{i+1}] (from {c['source']}) {c['text'][:1500]}" for i, c in enumerate(context_chunks))

    answer = llm.generate(
        f"Answer the question using ONLY the provided context chunks. Cite sources inline as [1], [2], etc. If the answer is not in the context, say so explicitly.\n\n"
        f"CONTEXT:\n{context}\n\nQUESTION: {question}",
        system="You are a precise retrieval-augmented answer engine. Never invent facts. Every claim must trace to a cited chunk. Be concise."
    )

    print(f"{'='*60}")
    print(f"ANSWER")
    print(f"{'='*60}")
    print(answer)
    print(f"\nSOURCES:")
    for i, c in enumerate(context_chunks, 1):
        print(f"  [{i}] {c['source']}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"question": question, "answer": answer, "sources": [c["source"] for c in context_chunks], "generated_at": datetime.now().isoformat()}, f, indent=2)
        print(f"\nSaved to {args.output}")
    return answer

def stats(args):
    """Show collection statistics."""
    data = _load_collection(args.name)
    chunks = data["chunks"]
    sources = Counter(c["source"] for c in chunks)
    total_chars = sum(len(c["text"]) for c in chunks)
    print(f"{'='*60}")
    print(f"COLLECTION: {data['name']}")
    print(f"{'='*60}")
    print(f"  Created:      {data.get('created', '?')}")
    print(f"  Chunks:       {len(chunks)}")
    print(f"  Sources:      {len(sources)} file(s)")
    print(f"  Total chars:  {total_chars:,}")
    if chunks:
        lens = [len(c["text"]) for c in chunks]
        print(f"  Chunk size:   min={min(lens)} avg={int(statistics.mean(lens))} max={max(lens)}")
    print(f"\n  SOURCES:")
    for src, count in sources.most_common(20):
        print(f"    {count:>4} chunks  {os.path.basename(src)}")

    base = os.path.join(os.path.dirname(__file__), "collections")
    if os.path.isdir(base):
        print(f"\n  ALL COLLECTIONS:")
        for fn in sorted(os.listdir(base)):
            if fn.endswith(".json"):
                with open(os.path.join(base, fn)) as f:
                    d = json.load(f)
                print(f"    {d['name']:<30} {len(d['chunks']):>5} chunks")
    return None

def main():
    import argparse
    p = argparse.ArgumentParser(prog="rag-engine", description="RAG engine with semantic search and cited generation")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("ingest", help="Ingest documents into a collection")
    i.add_argument("path"); i.add_argument("--name", default="default")
    i.set_defaults(fn=ingest)

    s = sub.add_parser("search", help="Semantic search over a collection")
    s.add_argument("query"); s.add_argument("--collection", default="default")
    s.add_argument("--top", type=int, default=5); s.add_argument("--output", default=None)
    s.set_defaults(fn=search)

    g = sub.add_parser("generate", help="Grounded generation with citations")
    g.add_argument("question"); g.add_argument("--collection", default="default")
    g.add_argument("--context", type=int, default=4); g.add_argument("--output", default=None)
    g.set_defaults(fn=generate)

    st = sub.add_parser("stats", help="Collection statistics")
    st.add_argument("--collection", default="default")
    st.set_defaults(fn=stats)

    args = p.parse_args()
    args.name = getattr(args, "name", getattr(args, "collection", "default"))
    args.fn(args)

if __name__ == '__main__':
    main()
