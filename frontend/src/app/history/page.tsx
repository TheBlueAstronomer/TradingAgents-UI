"use client";
import { useEffect, useState } from "react";
import { AnalysisHistory } from "@/components/AnalysisHistory";
import { getHistory } from "@/lib/api";
import type { HistoryPage, HistoryQuery } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
export default function HistoryPage() {
  const [query, setQuery] = useState<HistoryQuery>({
      page: 1,
      page_size: 20,
      sort_by: "created_at",
      sort_order: "desc",
    }),
    [page, setPage] = useState<HistoryPage | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    setPage(null);
    getHistory(query, c.signal)
      .then(setPage)
      .catch(() => {
        if (!c.signal.aborted) setError("Could not retrieve the docket index.");
      });
    return () => c.abort();
  }, [query]);
  return (
    <div className="history-page">
      <header className="page-heading">
        <span className="folio">Complete record</span>
        <h1>Docket index</h1>
        <p>Filter and reopen locally stored analysis records.</p>
      </header>
      <div className="filters">
        <Input
          aria-label="Filter by ticker"
          placeholder="Filter ticker"
          value={query.ticker || ""}
          onChange={(e) =>
            setQuery({ ...query, ticker: e.target.value, page: 1 })
          }
        />
        <Select
          aria-label="Filter by status"
          value={query.status || ""}
          onChange={(e) =>
            setQuery({
              ...query,
              status: e.target.value as HistoryQuery["status"],
              page: 1,
            })
          }
        >
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </Select>
        <Select
          aria-label="Filter by signal"
          value={query.signal || ""}
          onChange={(e) =>
            setQuery({
              ...query,
              signal: e.target.value as HistoryQuery["signal"],
              page: 1,
            })
          }
        >
          <option value="">All signals</option>
          {["BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL", "REVIEW"].map(
            (s) => (
              <option key={s}>{s}</option>
            ),
          )}
        </Select>
      </div>
      <AnalysisHistory
        page={page}
        query={query}
        loading={!page && !error}
        error={error}
        onQueryChange={setQuery}
      />
    </div>
  );
}
