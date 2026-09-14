import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import type { AnalysisSummary } from "@/lib/types";
import { DashboardDocketDesk } from "../DashboardDocketDesk";

const active: AnalysisSummary = {
  id: "run-active",
  ticker: "AME",
  analysis_date: "2026-09-14",
  asset_type: "stock",
  analysts: ["market"],
  llm_provider: "openai",
  research_depth: 1,
  status: "running",
  signal: null,
  created_at: "2026-09-14T10:00:00Z",
  started_at: "2026-09-14T10:01:00Z",
  completed_at: null,
};

test("links active work and the latest filing to their real dossiers", () => {
  const latest: AnalysisSummary = {
    ...active,
    id: "run-filed",
    ticker: "MP",
    status: "completed",
    signal: "HOLD",
    completed_at: "2026-09-14T10:12:00Z",
  };
  render(
    <DashboardDocketDesk
      activeRuns={[active]}
      latestRun={latest}
      latestExcerpt="The completed memorandum is ready for review."
      loading={false}
      error={null}
    />,
  );

  expect(screen.getByRole("heading", { name: "Active dockets" })).toBeVisible();
  expect(screen.getByRole("link", { name: /open AME live record/i })).toHaveAttribute(
    "href",
    "/analysis/run-active",
  );
  expect(screen.getByText("The completed memorandum is ready for review.")).toBeVisible();
  expect(screen.getByRole("link", { name: /open full dossier/i })).toHaveAttribute(
    "href",
    "/analysis/run-filed",
  );
});

test("shows truthful empty states without illustrative evidence", () => {
  render(
    <DashboardDocketDesk
      activeRuns={[]}
      latestRun={null}
      latestExcerpt={null}
      loading={false}
      error={null}
    />,
  );

  expect(screen.getByText("No analyses in flight.")).toBeVisible();
  expect(screen.getByText("No completed filing yet.")).toBeVisible();
  expect(screen.queryByText(/illustrative evidence/i)).toBeNull();
});
