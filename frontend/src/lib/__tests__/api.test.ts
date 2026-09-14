import { afterEach, expect, test, vi } from "vitest";
import { ApiClientError, createAnalysis, getHistory } from "../api";
afterEach(() => vi.unstubAllGlobals());
test("carries structured API metadata", () => {
  const error = new ApiClientError(422, "INVALID", "Invalid", "ticker");
  expect(error.field).toBe("ticker");
});

test("sends no-store JSON and returns structured API failures", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "INVALID_MODEL", message: "Bad model", field: "quick_think_llm" } }), { status: 422, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetch);
  await expect(createAnalysis({ ticker: "AAPL", analysis_date: "2025-01-01", analysts: ["market"], llm_provider: "openai", quick_think_llm: "bad", deep_think_llm: "deep", research_depth: 1 })).rejects.toMatchObject({ status: 422, code: "INVALID_MODEL", field: "quick_think_llm" });
  expect(fetch.mock.calls[0][1]).toMatchObject({ method: "POST", cache: "no-store" });
});

test("serializes only defined history query fields", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }), { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  await getHistory({ page: 1, page_size: 20, ticker: "", sort_by: "created_at", sort_order: "desc" });
  expect(fetch.mock.calls[0][0]).toContain("page=1&page_size=20&sort_by=created_at&sort_order=desc");
  expect(fetch.mock.calls[0][0]).not.toContain("ticker=");
});
