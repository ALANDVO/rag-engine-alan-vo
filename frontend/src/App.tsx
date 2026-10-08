import React, { useState } from "react";
import { AuthProvider } from "./context/AuthContext";
import { Navbar } from "./components/Navbar";
import { DocumentManager } from "./components/DocumentManager";
import { SearchWorkbench } from "./components/SearchWorkbench";
import { GroundedQA } from "./components/GroundedQA";
import { EvaluationDashboard } from "./components/EvaluationDashboard";
import { AuditLogView } from "./components/AuditLogView";

export const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("ingest");

  return (
    <div className="app-layout">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="main-content">
        {activeTab === "ingest" && <DocumentManager />}
        {activeTab === "search" && <SearchWorkbench />}
        {activeTab === "generate" && <GroundedQA />}
        {activeTab === "eval" && <EvaluationDashboard />}
        {activeTab === "audit" && <AuditLogView />}
      </main>

      <footer className="footer">
        <div className="footer-content">
          <span>
            <strong>rag-engine-alan-vo</strong> &bull; Built by{" "}
            <a href="https://github.com/ALANDVO" target="_blank" rel="noreferrer">
              Alan Vo
            </a>{" "}
            (&lt;alanvo@gmail.com&gt;)
          </span>
          <span className="footer-badge">AI, Machine Learning &amp; Cybersecurity</span>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
