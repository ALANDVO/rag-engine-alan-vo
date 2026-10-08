import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";

// Mock the apiClient methods
vi.mock("../api/client", () => ({
  apiClient: {
    getOIDCConfig: vi.fn().mockResolvedValue({ demo_mode: true }),
    loginDemo: vi.fn().mockResolvedValue({ access_token: "mock-token" }),
    getMe: vi.fn().mockResolvedValue({
      user_id: "demo-user",
      username: "demo-user",
      roles: ["operator"],
      effective_role: "operator",
      is_demo: true,
    }),
    listDocuments: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getStats: vi.fn().mockResolvedValue({
      total_documents: 2,
      total_chunks: 5,
      total_collections: 1,
      total_generations: 3,
      avg_faithfulness: 0.95,
    }),
    getEvaluationHistory: vi.fn().mockResolvedValue([]),
  },
  setAuthToken: vi.fn(),
  getAuthToken: vi.fn().mockReturnValue("mock-token"),
}));

describe("App Navigation and Workflows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the application brand and navigation tabs", async () => {
    render(<App />);

    expect(screen.getAllByText("rag-engine-alan-vo")[0]).toBeInTheDocument();
    expect(screen.getByText(/Alan Vo \| AI & Machine Learning/i)).toBeInTheDocument();
    expect(screen.getByText("Ingest & Chunks")).toBeInTheDocument();
    expect(screen.getByText("Hybrid Search")).toBeInTheDocument();
    expect(screen.getByText("Grounded Q&A")).toBeInTheDocument();
  });

  it("switches to Hybrid Search workbench when tab is clicked", async () => {
    render(<App />);

    const searchTab = screen.getByText("Hybrid Search");
    fireEvent.click(searchTab);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /Workflow 2: Hybrid Dense-Sparse Retrieval Workbench/i })
      ).toBeInTheDocument();
    });
  });

  it("switches to Grounded Q&A when tab is clicked", async () => {
    render(<App />);

    const qaTab = screen.getByText("Grounded Q&A");
    fireEvent.click(qaTab);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /Workflow 3: Grounded Citation Generation & Faithfulness Scoring/i })
      ).toBeInTheDocument();
    });
  });
});
