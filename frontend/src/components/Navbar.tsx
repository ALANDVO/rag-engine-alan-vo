import React from "react";
import { useAuth } from "../context/AuthContext";
import { UserRole } from "../types";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const { user, loginDemo, logout } = useAuth();

  const tabs = [
    { id: "ingest", label: "Ingest & Chunks" },
    { id: "search", label: "Hybrid Search" },
    { id: "generate", label: "Grounded Q&A" },
    { id: "eval", label: "AI/ML Benchmark" },
    { id: "audit", label: "Audit & Stats" },
  ];

  return (
    <header className="navbar">
      <div className="nav-brand">
        <span className="brand-title">rag-engine-alan-vo</span>
        <span className="brand-subtitle">Alan Vo | AI &amp; Machine Learning</span>
      </div>

      <nav className="nav-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="nav-auth">
        {user ? (
          <div className="user-info">
            <span className={`role-badge role-${user.effective_role}`}>
              {user.effective_role.toUpperCase()}
            </span>
            <span className="username">{user.username}</span>
            <div className="role-switcher">
              <label htmlFor="role-select">Switch:</label>
              <select
                id="role-select"
                value={user.effective_role}
                onChange={(e) => loginDemo(e.target.value as UserRole)}
              >
                <option value="viewer">Viewer</option>
                <option value="operator">Operator</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button className="btn-logout" onClick={logout}>
              Logout
            </button>
          </div>
        ) : (
          <div className="login-actions">
            <span>Demo:</span>
            <button className="btn-demo" onClick={() => loginDemo("operator")}>
              Login (Operator)
            </button>
            <button className="btn-demo" onClick={() => loginDemo("admin")}>
              Login (Admin)
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
