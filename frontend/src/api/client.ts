import {
  AuditLogEntry,
  ChunkItem,
  DocumentItem,
  EvaluationResult,
  GenerateResponse,
  SearchResponse,
  StatsResponse,
  UserSession,
} from "../types";

let currentToken: string | null = null;

export const setAuthToken = (token: string | null): void => {
  currentToken = token;
};

export const getAuthToken = (): string | null => {
  return currentToken;
};

const getBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    return envUrl.replace(/\/+$/, "");
  }
  return "/api";
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  if (currentToken) {
    headers.set("Authorization", `Bearer ${currentToken}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) {
        errorDetail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return null as unknown as T;
  }

  return response.json();
}

export const apiClient = {
  // Auth
  async getOIDCConfig(): Promise<{ client_id: string; issuer_url: string; audience: string; demo_mode: boolean }> {
    return request("/auth/config");
  },

  async loginDemo(role: string = "operator", username: string = "demo-user"): Promise<{ access_token: string }> {
    return request("/auth/demo-login", {
      method: "POST",
      body: JSON.stringify({ role, username }),
    });
  },

  async exchangeToken(code: string, codeVerifier: string, redirectUri: string): Promise<{ access_token: string }> {
    return request("/auth/token", {
      method: "POST",
      body: JSON.stringify({ code, code_verifier: codeVerifier, redirect_uri: redirectUri }),
    });
  },

  async getMe(): Promise<UserSession> {
    return request("/auth/me");
  },

  // Documents
  async ingestDocument(
    name: string,
    text: string,
    collection: string = "default",
    chunkSize: number = 800,
    chunkOverlap: number = 150
  ): Promise<DocumentItem> {
    return request("/documents/ingest", {
      method: "POST",
      body: JSON.stringify({
        name,
        text,
        collection,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      }),
    });
  },

  async listDocuments(collection?: string): Promise<{ items: DocumentItem[]; total: number }> {
    const q = collection ? `?collection=${encodeURIComponent(collection)}` : "";
    return request(`/documents${q}`);
  },

  async listChunks(documentId: string): Promise<{ items: ChunkItem[]; total: number }> {
    return request(`/documents/${documentId}/chunks`);
  },

  async deleteDocument(documentId: string): Promise<void> {
    return request(`/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  // Search
  async search(
    query: string,
    collection: string = "default",
    topK: number = 5,
    denseWeight: number = 0.5,
    sparseWeight: number = 0.5
  ): Promise<SearchResponse> {
    return request("/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        collection,
        top_k: topK,
        dense_weight: denseWeight,
        sparse_weight: sparseWeight,
      }),
    });
  },

  // Generation
  async generate(
    question: string,
    collection: string = "default",
    topK: number = 4
  ): Promise<GenerateResponse> {
    return request("/generate", {
      method: "POST",
      body: JSON.stringify({
        question,
        collection,
        top_k: topK,
      }),
    });
  },

  // Evaluation
  async runEvaluation(datasetName: string = "rag-benchmark-v1"): Promise<EvaluationResult> {
    return request("/evaluation/run", {
      method: "POST",
      body: JSON.stringify({ dataset_name: datasetName, top_k: 3 }),
    });
  },

  async getEvaluationHistory(): Promise<EvaluationResult[]> {
    return request("/evaluation/history");
  },

  // Audit & Stats
  async getAuditLogs(page: number = 1, size: number = 20): Promise<{ entries: AuditLogEntry[]; total: number }> {
    return request(`/audit?page=${page}&size=${size}`);
  },

  async getStats(): Promise<StatsResponse> {
    return request("/stats");
  },
};
