import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { AnalysisHistory } from "../AnalysisHistory";
test("teaches empty index", () => {
  render(
    <AnalysisHistory
      page={{ items: [], total: 0, page: 1, page_size: 20 }}
      query={{
        page: 1,
        page_size: 20,
        sort_by: "created_at",
        sort_order: "desc",
      }}
      loading={false}
      error={null}
      onQueryChange={() => {}}
    />,
  );
  expect(screen.getByText(/No dockets/)).toBeInTheDocument();
});

const query = { page: 1, page_size: 1, sort_by: "created_at" as const, sort_order: "desc" as const };
const row = { id: "abc", ticker: "AAPL", analysis_date: "2025-01-01", asset_type: "stock" as const, analysts: ["market"] as const, llm_provider: "openai", research_depth: 1, status: "completed" as const, signal: "BUY" as const, created_at: "2025-01-01T00:00:00Z", started_at: null, completed_at: null };
test("sorts, paginates, and links filed dockets", () => {
  const onQueryChange = vi.fn();
  render(<AnalysisHistory page={{ items: [row], total: 2, page: 1, page_size: 1 }} query={query} loading={false} error={null} onQueryChange={onQueryChange} />);
  fireEvent.click(screen.getByRole("button", { name: /ticker/i }));
  expect(onQueryChange).toHaveBeenCalledWith({ ...query, page: 1, sort_by: "ticker", sort_order: "desc" });
  fireEvent.click(screen.getByRole("button", { name: /next/i }));
  expect(onQueryChange).toHaveBeenLastCalledWith({ ...query, page: 2 });
  expect(screen.getByRole("link", { name: /view dossier/i })).toHaveAttribute("href", "/analysis/abc");
});

test("renders loading and API-failure states", () => {
  const { rerender } = render(<AnalysisHistory page={null} query={query} loading error={null} onQueryChange={() => {}} />);
  expect(screen.getByText(/loading index/i)).toBeInTheDocument();
  rerender(<AnalysisHistory page={null} query={query} loading={false} error="Unavailable" onQueryChange={() => {}} />);
  expect(screen.getByText("Unavailable")).toBeInTheDocument();
});
