import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { GroundedQA } from "../components/GroundedQA";
import { apiClient } from "../api/client";

vi.mock("../api/client", () => ({
  apiClient: {
    generate: vi.fn(),
  },
}));

describe("GroundedQA Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits question and renders grounded answer with citation badges and faithfulness score", async () => {
    const mockGenResponse = {
      question: "What is RAG?",
      answer: "RAG combines retrieval with generative models [1].",
      citations: [
        {
          index: 1,
          chunk_id: "chunk-1",
          document_name: "rag-overview.md",
          snippet: "RAG combines retrieval with generative models to ground outputs.",
          verified: true,
          overlap_score: 0.95,
        },
      ],
      faithfulness: {
        faithfulness_score: 1.0,
        citation_precision: 1.0,
        verified_claims_count: 1,
        total_citations_count: 1,
        advisory: true,
        summary: "High grounding: All claims trace directly to verified source context.",
      },
      provider: "deterministic-offline",
      model: "offline-rule-engine",
      execution_time_ms: 18.2,
    };

    (apiClient.generate as any).mockResolvedValue(mockGenResponse);

    render(<GroundedQA />);

    const questionInput = screen.getByLabelText(/Question/i);
    fireEvent.change(questionInput, { target: { value: "What is RAG?" } });

    const submitBtn = screen.getByRole("button", { name: /Generate Grounded Answer/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.generate).toHaveBeenCalledWith("What is RAG?", "default", 4);
      expect(screen.getByText("RAG combines retrieval with generative models [1].")).toBeInTheDocument();
      expect(screen.getByText(/Grounding: 100%/i)).toBeInTheDocument();
      expect(screen.getByText("Citation [1]")).toBeInTheDocument();
      expect(screen.getByText("rag-overview.md")).toBeInTheDocument();
      expect(screen.getByText("Verified Claim")).toBeInTheDocument();
    });
  });
});
