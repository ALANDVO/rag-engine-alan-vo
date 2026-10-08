import React, { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { AuditLogEntry, StatsResponse } from "../types";

export const AuditLogView: React.FC = () => {
  const { hasRole } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = hasRole("admin");

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const s = await apiClient.getStats();
      setStats(s);

      if (isAdmin) {
        const l = await apiClient.getAuditLogs();
        setLogs(l.entries);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load audit telemetry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [isAdmin]);

  return (
    <div className="section-container">
      <h2>System Telemetry &amp; Security Audit Trail</h2>
      <p className="section-desc">
        Operational telemetry and tamper-evident audit trail of data ingestions, queries, and role activities.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      {/* System Stats */}
      {stats && (
        <div className="grid-4col mb-4">
          <div className="metric-card">
            <span className="metric-title">Total Documents</span>
            <span className="metric-large">{stats.total_documents}</span>
            <span className="metric-sub">Across all collections</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Total Chunks</span>
            <span className="metric-large">{stats.total_chunks}</span>
            <span className="metric-sub">Dual-indexed representations</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Generations Handled</span>
            <span className="metric-large">{stats.total_generations}</span>
            <span className="metric-sub">Grounded Q&amp;A sessions</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Avg Faithfulness</span>
            <span className="metric-large">{(stats.avg_faithfulness * 100).toFixed(1)}%</span>
            <span className="metric-sub">System-wide score</span>
          </div>
        </div>
      )}

      {/* Audit Logs */}
      <div className="card">
        <div className="card-header">
          <h3>Security &amp; Mutation Audit Log</h3>
          <button className="btn-secondary" onClick={loadData} disabled={loading}>
            Refresh
          </button>
        </div>

        {!isAdmin ? (
          <div className="alert alert-info">
            Audit log records are restricted to users with the <strong>ADMIN</strong> role. Use the role switcher in the navbar to switch to Admin mode.
          </div>
        ) : logs.length === 0 ? (
          <div className="empty-state">No audit events recorded yet.</div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp (UTC)</th>
                  <th>Action</th>
                  <th>User ID</th>
                  <th>Role</th>
                  <th>Resource ID</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="timestamp-cell">{log.timestamp}</td>
                    <td>
                      <span className="action-tag">{log.action}</span>
                    </td>
                    <td>{log.user_id}</td>
                    <td>
                      <span className={`badge role-${log.user_role}`}>{log.user_role}</span>
                    </td>
                    <td><code>{log.resource_id || "-"}</code></td>
                    <td>{log.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
