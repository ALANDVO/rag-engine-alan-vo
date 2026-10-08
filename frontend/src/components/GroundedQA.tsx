import React, { useState } from "react";
import { apiClient } from "../api/client";
import { GenerateResponse } from "../types";

export const GroundedQA: React.FC = () => {
  const [question, setQuestion] = useState<string>("");
  const [collection, setCollection] = useState<string>("default");
  const [topK, setTopK] = useState<number>(4);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [activeCitationIndex, setActiveCitationIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.generate(question, collection, topK);
      setResult(res);
      setActiveCitationIndex(null);
    } catch (err: any) {
      setError(err.message || "Failed to generate grounded answer.");
    } finally {
      setLoading(false);
    }
  };

  const loadSampleQuestion = () => {
    setQuestion("How does the RAG architecture combine dense embeddings and sparse BM25 indexing?");
  };

  return (
    <div className="section-container">
      <h2>Workflow 3: Grounded Citation Generation &amp; Faithfulness Scoring</h2>
      <p className="section-desc">
        Ask questions over indexed collections. Every answer is grounded with explicit inline source citations, verified against source chunks, and scored for hallucinations.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="card-header">
          <h3>Ask a Grounded Question</h3>
          <button type="button" className="btn-secondary" onClick={loadSampleQuestion}>
            Sample Question
          </button>
        </div>

        <form onSubmit={handleAsk}>
          <div className="form-group">
            <label htmlFor="qa-input">Question</label>
            <input
              id="qa-input"
              type="text"
              placeholder="e.g. What are the key components of the RAG ingestion pipeline?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
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
              <label>Context Depth (Chunks): {topK}</label>
              <input
                type="range"
                min={1}
                max={8}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Retrieving & Synthesizing..." : "Generate Grounded Answer"}
          </button>
        </form>
      </div>

      {result && (
        <div className="qa-response-area mt-4">
          {/* Faithfulness Scorecard */}
          <div className="card score-card">
            <div className="score-header">
              <h3>Faithfulness &amp; Citation Attribution Audit</h3>
              <span
                className={`faith-badge ${
                  result.faithfulness.faithfulness_score >= 0.8
                    ? "faith-high"
                    : result.faithfulness.faithfulness_score >= 0.5
                    ? "faith-med"
                    : "faith-low"
                }`}
              >
                Grounding: {Math.round(result.faithfulness.faithfulness_score * 100)}%
              </span>
            </div>

            <p className="score-summary">{result.faithfulness.summary}</p>
            <div className="metrics-row">
              <div className="metric-box">
                <span className="metric-val">{result.faithfulness.verified_claims_count}</span>
                <span className="metric-lbl">Verified Citations</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{result.faithfulness.total_citations_count}</span>
                <span className="metric-lbl">Total Citations</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{result.provider}</span>
                <span className="metric-lbl">Engine Provider</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{result.execution_time_ms} ms</span>
                <span className="metric-lbl">Synthesis Latency</span>
              </div>
            </div>
          </div>

          {/* Generated Answer */}
          <div className="card mt-3">
            <div className="answer-header">
              <h3>Answer</h3>
              <span className="advisory-pill">Advisory AI Output</span>
            </div>
            <div className="answer-body">{result.answer}</div>
          </div>

          {/* Source Citations */}
          <div className="card mt-3">
            <h3>Cited Source Evidence ({result.citations.length})</h3>
            <div className="citations-grid">
              {result.citations.map((c) => (
                <div
                  key={c.index}
                  className={`citation-card ${activeCitationIndex === c.index ? "active-citation" : ""}`}
                  onClick={() => setActiveCitationIndex(c.index)}
                >
                  <div className="citation-header">
                    <span className="citation-pill">Citation [{c.index}]</span>
                    <span className="citation-doc">{c.document_name}</span>
                    <span className={`status-pill ${c.verified ? "verified" : "unverified"}`}>
                      {c.verified ? "Verified Claim" : "Ungrounded"}
                    </span>
                  </div>
                  <div className="citation-snippet">{c.snippet}</div>
                  <div className="citation-footer">
                    Lexical Overlap Alignment: {(c.overlap_score * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
