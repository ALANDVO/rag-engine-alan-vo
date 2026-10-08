import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SearchWorkbench } from "../components/SearchWorkbench";
import { apiClient } from "../api/client";

vi.mock("../api/client", () => ({
  apiClient: {
    search: vi.fn(),
  },
}));

describe("SearchWorkbench Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("executes hybrid search and displays ranked results with scores", async () => {
    const mockSearchResults = {
      query: "reciprocal rank fusion",
      collection: "default",
      total_results: 1,
      results: [
        {
          rank: 1,
          chunk_id: "doc-1_c0",
          document_id: "doc-1",
          document_name: "architecture.md",
          score: 0.88,
          dense_score: 0.85,
          sparse_score: 0.91,
          text: "Reciprocal rank fusion fuses dense cosine similarity with sparse BM25 scores.",
          heading: "Hybrid Fusion",
        },
      ],
      search_time_ms: 12.5,
    };

    (apiClient.search as any).mockResolvedValue(mockSearchResults);

    render(<SearchWorkbench />);

    const searchInput = screen.getByLabelText(/Search Query/i);
    fireEvent.change(searchInput, { target: { value: "reciprocal rank fusion" } });

    const searchButton = screen.getByRole("button", { name: /Execute Hybrid Search/i });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(apiClient.search).toHaveBeenCalledWith(
        "reciprocal rank fusion",
        "default",
        5,
        0.5,
        0.5
      );
      expect(screen.getByText("Rank #1")).toBeInTheDocument();
      expect(screen.getByText("architecture.md")).toBeInTheDocument();
      expect(screen.getByText(/Reciprocal rank fusion fuses dense cosine similarity/i)).toBeInTheDocument();
      expect(screen.getByText(/Hybrid: 88.0%/i)).toBeInTheDocument();
    });
  });
});
