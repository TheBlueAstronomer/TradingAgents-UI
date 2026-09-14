"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FileWarning } from "lucide-react";
import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { AgentProgress } from "@/components/AgentProgress";
import { ReportViewer } from "@/components/ReportViewer";
import { SignalBadge } from "@/components/SignalBadge";
export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const stream = useAnalysisStream(id);
  if (stream.error && !stream.run)
    return (
      <section className="route-state">
        <FileWarning size={28} />
        <h1>Docket unavailable</h1>
        <p>{stream.error}</p>
        <Link href="/">Return to new analysis</Link>
      </section>
    );
  const run = stream.run;
  return (
    <div className="analysis-page">
      {!run ? (
        <section className="route-state">
          <h1>Opening docket…</h1>
          <p>The persisted research record is being retrieved.</p>
        </section>
      ) : (
        <>
          <header className="analysis-heading">
            <div>
              <span className="folio">Docket {run.id.slice(0, 8)}</span>
              <h1>{run.ticker} research record</h1>
              <p>
                {run.analysis_date} · {run.asset_type} · {run.research_depth}{" "}
                research round{run.research_depth > 1 ? "s" : ""}
              </p>
            </div>
            <div>
              <span className={`status-stamp ${run.status}`}>{run.status}</span>
              <SignalBadge signal={run.signal} size="md" />
            </div>
          </header>
          <p className="sr-only" aria-live="polite">
            {stream.connection}. {run.status}
          </p>
          {stream.error && (
            <p className="error-note" role="status">
              {run.status === "failed" && run.error_message
                ? run.error_message
                : stream.error}{" "}
              Refresh this docket or return to the index to review the persisted
              record.
            </p>
          )}
          {run.status === "failed" && !stream.error && run.error_message && (
            <p className="error-note" role="status">
              {run.error_message} Refresh this docket after correcting the local
              backend configuration.
            </p>
          )}
          <AgentProgress
            statuses={run.agent_statuses}
            selectedAnalysts={run.analysts}
            messages={stream.messages}
            connection={stream.connection}
          />
          <ReportViewer
            reports={run.reports}
            selectedAnalysts={run.analysts}
            loading={false}
          />
        </>
      )}
    </div>
  );
}
