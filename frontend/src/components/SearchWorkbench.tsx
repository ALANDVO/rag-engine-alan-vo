import React, { useState } from "react";
import { apiClient } from "../api/client";
import { SearchResponse, SearchResultItem } from "../types";

export const SearchWorkbench: React.FC = () => {
  const [query, setQuery] = useState<string>("");
  const [collection, setCollection] = useState<string>("default");
  const [denseWeight, setDenseWeight] = useState<number>(0.5);
  const [topK, setTopK] = useState<number>(5);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [searchMeta, setSearchMeta] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setError("Please enter a search query.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const sparseWeight = Math.round((1.0 - denseWeight) * 10) / 10;
      const res = await apiClient.search(query, collection, topK, denseWeight, sparseWeight);
      setResults(res.results);
      setSearchMeta(res);
    } catch (err: any) {
      setError(err.message || "Search request failed.");
    } finally {
      setLoading(false);
    }
  };

  const sparseWeight = Math.round((1.0 - denseWeight) * 10) / 10;

  return (
    <div className="section-container">
      <h2>Workflow 2: Hybrid Dense-Sparse Retrieval Workbench</h2>
      <p className="section-desc">
        Perform hybrid retrieval combining exact lexical BM25 matching and semantic cosine vector similarity with adjustable fusion weights.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <form onSubmit={handleSearch}>
          <div className="form-group">
            <label htmlFor="search-input">Search Query</label>
            <input
              id="search-input"
              type="text"
              placeholder="e.g. How does reciprocal rank fusion combine embeddings and keywords?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
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
              <label>Top Results (K): {topK}</label>
              <input
                type="range"
                min={1}
                max={15}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label>
                Fusion Weights: Dense {Math.round(denseWeight * 100)}% / Sparse {Math.round(sparseWeight * 100)}%
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={denseWeight}
                onChange={(e) => setDenseWeight(Number(e.target.value))}
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Searching..." : "Execute Hybrid Search"}
          </button>
        </form>
      </div>

      {searchMeta && (
        <div className="search-stats">
          Found <strong>{searchMeta.total_results}</strong> relevant chunks in{" "}
          <strong>{searchMeta.search_time_ms} ms</strong> for collection "{searchMeta.collection}".
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results-list">
          {results.map((r) => (
            <div key={r.chunk_id} className="result-card">
              <div className="result-header">
                <span className="rank-badge">Rank #{r.rank}</span>
                <span className="doc-badge">{r.document_name}</span>
                {r.heading && <span className="heading-badge">{r.heading}</span>}
                <div className="score-group">
                  <span className="score-total" title="Fused hybrid score">
                    Hybrid: {(r.score * 100).toFixed(1)}%
                  </span>
                  <span className="score-sub" title="Cosine vector similarity">
                    Dense: {(r.dense_score * 100).toFixed(1)}%
                  </span>
                  <span className="score-sub" title="BM25 keyword score">
                    Sparse: {(r.sparse_score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="result-body">{r.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
