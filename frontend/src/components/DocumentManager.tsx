import React, { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ChunkItem, DocumentItem } from "../types";

export const DocumentManager: React.FC = () => {
  const { hasRole } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [name, setName] = useState<string>("");
  const [text, setText] = useState<string>("");
  const [collection, setCollection] = useState<string>("default");
  const [chunkSize, setChunkSize] = useState<number>(600);
  const [chunkOverlap, setChunkOverlap] = useState<number>(100);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canEdit = hasRole("operator");

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const res = await apiClient.listDocuments(collection);
      setDocuments(res.items);
    } catch (err: any) {
      setError(err.message || "Failed to load documents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [collection]);

  const loadChunks = async (docId: string) => {
    try {
      setSelectedDocId(docId);
      const res = await apiClient.listChunks(docId);
      setChunks(res.items);
    } catch (err: any) {
      setError(err.message || "Failed to load chunks.");
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !text.trim()) {
      setError("Please provide both document name and text content.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      const doc = await apiClient.ingestDocument(name, text, collection, chunkSize, chunkOverlap);
      setSuccess(`Successfully ingested "${doc.name}" into ${doc.chunk_count} chunks.`);
      setName("");
      setText("");
      await loadDocuments();
      await loadChunks(doc.id);
    } catch (err: any) {
      setError(err.message || "Failed to ingest document.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    try {
      setLoading(true);
      await apiClient.deleteDocument(docId);
      if (selectedDocId === docId) {
        setSelectedDocId(null);
        setChunks([]);
      }
      await loadDocuments();
    } catch (err: any) {
      setError(err.message || "Failed to delete document.");
    } finally {
      setLoading(false);
    }
  };

  const loadSample = () => {
    setName("rag-architecture-guide.md");
    setText(`# Retrieval-Augmented Generation Architecture

Retrieval-Augmented Generation (RAG) optimizes LLM outputs by referencing an authoritative knowledge base outside of its training data sources before generating a response.

## Chunking & Ingestion Strategy
Effective RAG requires splitting documents into cohesive semantic units. Paragraph-based chunking with a 150-token sliding overlap prevents truncation of multi-sentence ideas.

## Hybrid Dense & Sparse Retrieval
While dense vector embeddings excel at semantic paraphrasing, sparse BM25 indexing guarantees exact matches for technical terminology, identifiers, and codes. Combining both via Reciprocal Rank Fusion ensures maximum recall and precision.

## Grounded Citation Attribution
Every generated response must explicitly map claims to retrieved source chunks [1]. Evaluating token overlap and n-gram alignment provides real-time faithfulness and hallucination detection.`);
  };

  return (
    <div className="section-container">
      <h2>Workflow 1: Document Ingestion &amp; Chunk Indexing</h2>
      <p className="section-desc">
        Ingest text or markdown documents, perform paragraph-boundary chunking with overlap, and index dual representations into SQLite.
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="grid-2col">
        {/* Ingest Form */}
        <div className="card">
          <div className="card-header">
            <h3>Ingest Document</h3>
            <button type="button" className="btn-secondary" onClick={loadSample}>
              Load Sample Text
            </button>
          </div>

          <form onSubmit={handleIngest}>
            <div className="form-group">
              <label>Document Name</label>
              <input
                type="text"
                placeholder="e.g. system-spec.md"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={!canEdit || loading}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Collection</label>
                <input
                  type="text"
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="form-group">
                <label>Chunk Size (chars)</label>
                <input
                  type="number"
                  value={chunkSize}
                  onChange={(e) => setChunkSize(Number(e.target.value))}
                  disabled={!canEdit || loading}
                />
              </div>
              <div className="form-group">
                <label>Overlap (chars)</label>
                <input
                  type="number"
                  value={chunkOverlap}
                  onChange={(e) => setChunkOverlap(Number(e.target.value))}
                  disabled={!canEdit || loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Document Content</label>
              <textarea
                rows={8}
                placeholder="Paste markdown or plain text here..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={!canEdit || loading}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={!canEdit || loading}>
              {loading ? "Processing..." : "Chunk & Ingest Document"}
            </button>
            {!canEdit && (
              <span className="hint-text"> (Operator or Admin role required to ingest)</span>
            )}
          </form>
        </div>

        {/* Document List */}
        <div className="card">
          <div className="card-header">
            <h3>Indexed Documents ({documents.length})</h3>
            <button className="btn-secondary" onClick={loadDocuments} disabled={loading}>
              Refresh
            </button>
          </div>

          {documents.length === 0 ? (
            <div className="empty-state">No documents indexed yet. Use the form to ingest one.</div>
          ) : (
            <ul className="doc-list">
              {documents.map((d) => (
                <li
                  key={d.id}
                  className={`doc-item ${selectedDocId === d.id ? "selected" : ""}`}
                  onClick={() => loadChunks(d.id)}
                >
                  <div className="doc-meta">
                    <strong>{d.name}</strong>
                    <span className="badge">{d.chunk_count} chunks</span>
                    <span className="doc-chars">{d.char_count} chars</span>
                  </div>
                  {canEdit && (
                    <button
                      className="btn-danger-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(d.id);
                      }}
                    >
                      Delete
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Chunk Viewer */}
      {selectedDocId && (
        <div className="card mt-4">
          <h3>Generated Chunks for Selected Document ({chunks.length})</h3>
          <div className="chunks-grid">
            {chunks.map((c) => (
              <div key={c.id} className="chunk-card">
                <div className="chunk-header">
                  <span className="chunk-index">Chunk #{c.chunk_index + 1}</span>
                  {c.heading && <span className="chunk-heading">{c.heading}</span>}
                  <span className="chunk-tokens">{c.token_count} tokens</span>
                </div>
                <div className="chunk-body">{c.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
