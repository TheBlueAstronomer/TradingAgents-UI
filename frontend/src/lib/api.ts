import type {
  AnalysisCreate,
  AnalysisDetail,
  AnalysisSummary,
  AnalystOption,
  HistoryPage,
  HistoryQuery,
  ProviderOption,
} from "./types";
const base = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/$/, "");
export class ApiClientError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public field?: string,
  ) {
    super(message);
  }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(base + path, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const d = payload.detail || {};
    throw new ApiClientError(
      res.status,
      d.code || "REQUEST_FAILED",
      d.message || "Request failed",
      d.field,
    );
  }
  return res.json();
}
export const createAnalysis = (input: AnalysisCreate, signal?: AbortSignal) =>
  request<AnalysisSummary>("/api/analysis", {
    method: "POST",
    body: JSON.stringify(input),
    signal,
  });
export const getAnalysis = (id: string, signal?: AbortSignal) =>
  request<AnalysisDetail>(`/api/analysis/${id}`, { signal });
export const getProviders = (signal?: AbortSignal) =>
  request<ProviderOption[]>("/api/config/providers", { signal });
export const getAnalysts = (signal?: AbortSignal) =>
  request<AnalystOption[]>("/api/config/analysts", { signal });
export const getHistory = (q: HistoryQuery, signal?: AbortSignal) =>
  request<HistoryPage>(
    "/api/history?" +
      new URLSearchParams(
        Object.entries(q)
          .filter(([, v]) => v !== undefined && v !== "")
          .map(([k, v]) => [k, String(v)]),
      ),
    { signal },
  );
