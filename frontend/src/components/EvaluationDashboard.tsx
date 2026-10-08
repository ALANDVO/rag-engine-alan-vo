import React, { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { EvaluationResult } from "../types";

export const EvaluationDashboard: React.FC = () => {
  const { hasRole } = useAuth();
  const [currentEval, setCurrentEval] = useState<EvaluationResult | null>(null);
  const [history, setHistory] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const canRun = hasRole("operator");

  const loadHistory = async () => {
    try {
      const res = await apiClient.getEvaluationHistory();
      setHistory(res);
      if (res.length > 0 && !currentEval) {
        setCurrentEval(res[0]);
      }
    } catch {
      // History optional
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleRunEvaluation = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.runEvaluation("rag-benchmark-v1");
      setCurrentEval(res);
      await loadHistory();
    } catch (err: any) {
      setError(err.message || "Failed to execute evaluation benchmark.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section-container">
      <h2>AI/ML Evaluation &amp; Benchmark Dashboard</h2>
      <p className="section-desc">
        Evaluate retrieval accuracy and faithfulness metrics across standardized ground-truth benchmark queries.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="card-header">
          <div>
            <h3>Benchmark Suite: rag-benchmark-v1</h3>
            <span className="hint-text">
              Dual-encoder and BM25 ranking evaluation with gold-standard query associations.
            </span>
          </div>
          <button
            className="btn-primary"
            onClick={handleRunEvaluation}
            disabled={!canRun || loading}
          >
            {loading ? "Evaluating Benchmark..." : "Run AI/ML Benchmark"}
          </button>
        </div>
        {!canRun && (
          <div className="hint-text mt-2">
            (Operator or Admin role required to trigger new evaluation runs)
          </div>
        )}
      </div>

      {currentEval && (
        <div className="mt-4">
          {/* Metrics summary cards */}
          <div className="grid-4col">
            <div className="metric-card">
              <span className="metric-title">Mean Reciprocal Rank (MRR)</span>
              <span className="metric-large">
                {(currentEval.metrics.mrr * 100).toFixed(1)}%
              </span>
              <span className="metric-sub">Rank-weighted relevance</span>
            </div>
            <div className="metric-card">
              <span className="metric-title">Hit Rate @ 1</span>
              <span className="metric-large">
                {(currentEval.metrics.hit_rate_1 * 100).toFixed(1)}%
              </span>
              <span className="metric-sub">Top-1 accuracy</span>
            </div>
            <div className="metric-card">
              <span className="metric-title">Hit Rate @ 3</span>
              <span className="metric-large">
                {(currentEval.metrics.hit_rate_3 * 100).toFixed(1)}%
              </span>
              <span className="metric-sub">Top-3 recall</span>
            </div>
            <div className="metric-card">
              <span className="metric-title">Avg Faithfulness</span>
              <span className="metric-large">
                {(currentEval.metrics.avg_faithfulness * 100).toFixed(1)}%
              </span>
              <span className="metric-sub">Grounded claim alignment</span>
            </div>
          </div>

          {/* Benchmark Queries Table */}
          <div className="card mt-4">
            <h3>Benchmark Query Breakdown ({currentEval.sample_details.length} samples)</h3>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Query</th>
                    <th>Target Document</th>
                    <th>Top Retrieved</th>
                    <th>Found Rank</th>
                    <th>Hybrid Score</th>
                    <th>Faithfulness</th>
                  </tr>
                </thead>
                <tbody>
                  {currentEval.sample_details.map((s, idx) => (
                    <tr key={idx}>
                      <td className="query-cell">{s.query}</td>
                      <td><code>{s.target_doc}</code></td>
                      <td>{s.retrieved_top}</td>
                      <td>
                        <span className={`badge ${s.first_rank === 1 ? "badge-success" : "badge-warn"}`}>
                          Rank #{s.first_rank}
                        </span>
                      </td>
                      <td>{(s.score * 100).toFixed(1)}%</td>
                      <td>{(s.faithfulness * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
