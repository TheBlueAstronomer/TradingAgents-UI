"use client";

import Link from "next/link";
import { ArrowRight, Clock3, FileCheck2 } from "lucide-react";
import type { AnalysisSummary } from "@/lib/types";
import { SignalBadge } from "./SignalBadge";

function formatMoment(value: string | null) {
  if (!value) return "Waiting to start";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function DashboardDocketDesk({
  activeRuns,
  latestRun,
  latestExcerpt,
  loading,
  error,
}: {
  activeRuns: AnalysisSummary[];
  latestRun: AnalysisSummary | null;
  latestExcerpt: string | null;
  loading: boolean;
  error: string | null;
}) {
  return (
    <div className="evidence-column dashboard-desk">
      <section
        className="dashboard-panel active-dockets"
        aria-labelledby="active-dockets-title"
      >
        <header>
          <div>
            <span className="folio">Operations desk</span>
            <h2 id="active-dockets-title">Active dockets</h2>
            <p>Queued and running analyses ready to resume.</p>
          </div>
          <span
            className="desk-count"
            aria-label={`${activeRuns.length} active dockets`}
          >
            {activeRuns.length} active
          </span>
        </header>

        {error ? (
          <p className="desk-note error-note" role="status">
            {error}
          </p>
        ) : loading ? (
          <p className="desk-note">Checking the operations queue…</p>
        ) : activeRuns.length ? (
          <ol className="active-docket-list">
            {activeRuns.map((run) => (
              <li key={run.id}>
                <Link
                  className="active-docket-row"
                  href={`/analysis/${run.id}`}
                >
                  <span
                    className={`active-run-mark ${run.status}`}
                    aria-hidden="true"
                  />
                  <span className="active-docket-copy">
                    <span className="active-docket-title">
                      <strong>{run.ticker}</strong>
                      <span>{run.status}</span>
                    </span>
                    <small>
                      <Clock3 aria-hidden="true" size={13} />
                      {run.status === "running" ? "Started" : "Queued"}{" "}
                      {formatMoment(run.started_at || run.created_at)}
                    </small>
                  </span>
                  <ArrowRight
                    className="row-arrow"
                    aria-hidden="true"
                    size={18}
                  />
                  <span className="sr-only">Open {run.ticker} live record</span>
                </Link>
              </li>
            ))}
          </ol>
        ) : (
          <div className="desk-empty">
            <strong>No analyses in flight.</strong>
            <p>A newly submitted docket will appear here until it is filed.</p>
          </div>
        )}
      </section>

      <section
        className="dashboard-panel latest-filing"
        aria-labelledby="latest-filing-title"
      >
        <header>
          <div>
            <span className="folio">Recently concluded</span>
            <h2 id="latest-filing-title">Latest filing</h2>
          </div>
          {latestRun && <SignalBadge signal={latestRun.signal} size="md" />}
        </header>

        {loading && !latestRun ? (
          <p className="desk-note">Opening the latest filed record…</p>
        ) : latestRun ? (
          <div className="latest-filing-body">
            <div className="filing-identity">
              <FileCheck2 aria-hidden="true" size={22} />
              <div>
                <strong>{latestRun.ticker} research record</strong>
                <span>
                  Filed {formatMoment(latestRun.completed_at)} · Analysis date{" "}
                  {latestRun.analysis_date}
                </span>
              </div>
            </div>
            <p className="filing-excerpt">
              {latestExcerpt ||
                "The final memorandum and its supporting evidence are available in the dossier."}
            </p>
            <Link
              className="latest-filing-link"
              href={`/analysis/${latestRun.id}`}
            >
              Open full dossier
              <ArrowRight aria-hidden="true" size={17} />
            </Link>
          </div>
        ) : (
          <div className="desk-empty">
            <strong>No completed filing yet.</strong>
            <p>The first completed analysis will be summarized here.</p>
          </div>
        )}
      </section>
    </div>
  );
}
