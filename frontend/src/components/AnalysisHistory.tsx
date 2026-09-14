"use client";
import Link from "next/link";
import { ArrowDownUp, ChevronLeft, ChevronRight } from "lucide-react";
import type { HistoryPage, HistoryQuery } from "@/lib/types";
import { SignalBadge } from "./SignalBadge";
import { Button } from "./ui/button";
export function AnalysisHistory({
  page,
  query,
  loading,
  error,
  onQueryChange,
}: {
  page: HistoryPage | null;
  query: HistoryQuery;
  loading: boolean;
  error: string | null;
  onQueryChange: (q: HistoryQuery) => void;
}) {
  const sort = (key: HistoryQuery["sort_by"]) =>
    onQueryChange({
      ...query,
      sort_by: key,
      sort_order:
        query.sort_by === key && query.sort_order === "desc" ? "asc" : "desc",
      page: 1,
    });
  if (error)
    return (
      <section className="history-band">
        <h2>Recent dockets</h2>
        <p className="error-note">{error}</p>
      </section>
    );
  return (
    <section className="history-band" aria-labelledby="recent-dockets">
      <header>
        <div>
          <span className="folio">Docket index</span>
          <h2 id="recent-dockets">Recent dockets</h2>
        </div>
        <Link href="/history">Open complete index</Link>
      </header>
      {loading ? (
        <p>Loading index…</p>
      ) : !page?.items.length ? (
        <div className="empty-state">
          <strong>No dockets filed yet.</strong>
          <p>
            Open an analysis above; completed and interrupted work remains here
            for review.
          </p>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="docket-table">
              <thead>
                <tr>
                  {(["ticker", "analysis_date", "status"] as const).map((k) => (
                    <th key={k}>
                      <button onClick={() => sort(k)}>
                        {k.replace("_", " ")} <ArrowDownUp size={13} />
                      </button>
                    </th>
                  ))}
                  <th>Signal</th>
                  <th>Open</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((run) => (
                  <tr key={run.id}>
                    <td data-label="Ticker">{run.ticker}</td>
                    <td data-label="Date">{run.analysis_date}</td>
                    <td data-label="Status">
                      <span className="status-word">{run.status}</span>
                    </td>
                    <td data-label="Signal">
                      <SignalBadge signal={run.signal} />
                    </td>
                    <td data-label="Open">
                      <Link href={`/analysis/${run.id}`}>View dossier</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <footer>
            <span>
              {page.total} filed docket{page.total === 1 ? "" : "s"}
            </span>
            <span>
              <Button
                disabled={query.page === 1}
                onClick={() =>
                  onQueryChange({ ...query, page: query.page - 1 })
                }
              >
                <ChevronLeft /> Previous
              </Button>
              <Button
                disabled={query.page * query.page_size >= page.total}
                onClick={() =>
                  onQueryChange({ ...query, page: query.page + 1 })
                }
              >
                Next <ChevronRight />
              </Button>
            </span>
          </footer>
        </>
      )}
    </section>
  );
}
