"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnalysisForm } from "@/components/AnalysisForm";
import { DashboardDocketDesk } from "@/components/DashboardDocketDesk";
import { AnalysisHistory } from "@/components/AnalysisHistory";
import { getAnalysis, getAnalysts, getHistory, getProviders } from "@/lib/api";
import type {
  AnalysisSummary,
  AnalystOption,
  HistoryPage,
  HistoryQuery,
  ProviderOption,
} from "@/lib/types";

function memorandumExcerpt(markdown: string | undefined) {
  if (!markdown) return null;
  const text = markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1")
    .replace(/[#>*_`|~-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return text.length > 280 ? `${text.slice(0, 277).trimEnd()}…` : text;
}

export default function Dashboard() {
  const router = useRouter();
  const [providers, setProviders] = useState<ProviderOption[]>([]),
    [analysts, setAnalysts] = useState<AnalystOption[]>([]),
    [history, setHistory] = useState<HistoryPage | null>(null),
    [error, setError] = useState("");
  const [activeRuns, setActiveRuns] = useState<AnalysisSummary[]>([]),
    [latestRun, setLatestRun] = useState<AnalysisSummary | null>(null),
    [latestExcerpt, setLatestExcerpt] = useState<string | null>(null),
    [deskLoading, setDeskLoading] = useState(true),
    [deskError, setDeskError] = useState<string | null>(null);
  const [query, setQuery] = useState<HistoryQuery>({
    page: 1,
    page_size: 5,
    sort_by: "created_at",
    sort_order: "desc",
  });
  useEffect(() => {
    const c = new AbortController();
    Promise.all([getProviders(c.signal), getAnalysts(c.signal)])
      .then(([p, a]) => {
        setProviders(p);
        setAnalysts(a);
      })
      .catch(() => {
        if (!c.signal.aborted) {
          setError(
            "The local backend is unavailable. Start it, then reload this page.",
          );
        }
      });
    return () => c.abort();
  }, []);
  useEffect(() => {
    const c = new AbortController();
    getHistory(query, c.signal)
      .then(setHistory)
      .catch(() => {
        if (!c.signal.aborted)
          setError("The docket index could not be loaded.");
      });
    return () => c.abort();
  }, [query]);
  useEffect(() => {
    const controller = new AbortController();
    let refreshing = false;
    const loadDesk = async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const baseQuery = {
          page: 1,
          page_size: 5,
          sort_by: "created_at" as const,
        };
        const [running, queued, completed] = await Promise.all([
          getHistory(
            { ...baseQuery, status: "running", sort_order: "desc" },
            controller.signal,
          ),
          getHistory(
            { ...baseQuery, status: "queued", sort_order: "asc" },
            controller.signal,
          ),
          getHistory(
            {
              ...baseQuery,
              page_size: 1,
              status: "completed",
              sort_order: "desc",
            },
            controller.signal,
          ),
        ]);
        if (controller.signal.aborted) return;
        setActiveRuns(
          [...running.items, ...queued.items].filter(
            (run) => run.status === "running" || run.status === "queued",
          ),
        );
        const latest =
          completed.items.find((run) => run.status === "completed") || null;
        setLatestRun(latest);
        setDeskError(null);
        if (latest) {
          try {
            const detail = await getAnalysis(latest.id, controller.signal);
            if (!controller.signal.aborted)
              setLatestExcerpt(
                memorandumExcerpt(detail.reports.final_trade_decision),
              );
          } catch {
            if (!controller.signal.aborted) setLatestExcerpt(null);
          }
        } else {
          setLatestExcerpt(null);
        }
      } catch {
        if (!controller.signal.aborted)
          setDeskError("The active docket desk could not be refreshed.");
      } finally {
        if (!controller.signal.aborted) setDeskLoading(false);
        refreshing = false;
      }
    };
    void loadDesk();
    const interval = window.setInterval(loadDesk, 8000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, []);
  return (
    <div className="docket-layout">
      <div className="work-surface">
        <AnalysisForm
          providers={providers}
          analysts={analysts}
          onCreated={(r) => router.push(`/analysis/${r.id}`)}
        />
        <DashboardDocketDesk
          activeRuns={activeRuns}
          latestRun={latestRun}
          latestExcerpt={latestExcerpt}
          loading={deskLoading}
          error={deskError}
        />
      </div>
      <AnalysisHistory
        page={history}
        query={query}
        loading={!history && !error}
        error={error}
        onQueryChange={setQuery}
      />
    </div>
  );
}
