"use client";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AnalystKey, ReportKey } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
const all: { key: ReportKey; label: string; analyst?: AnalystKey }[] = [
  { key: "market_report", label: "Market", analyst: "market" },
  { key: "sentiment_report", label: "Sentiment", analyst: "social" },
  { key: "news_report", label: "News", analyst: "news" },
  {
    key: "fundamentals_report",
    label: "Fundamentals",
    analyst: "fundamentals",
  },
  { key: "investment_plan", label: "Research" },
  { key: "trader_investment_plan", label: "Trading" },
  { key: "final_trade_decision", label: "Final memorandum" },
];
export function ReportViewer({
  reports,
  selectedAnalysts,
  loading,
}: {
  reports: Partial<Record<ReportKey, string>>;
  selectedAnalysts: AnalystKey[];
  loading: boolean;
}) {
  const sections = all.filter(
    (s) => !s.analyst || selectedAnalysts.includes(s.analyst),
  );
  const first = sections.find((s) => reports[s.key])?.key || sections[0].key;
  const [tab, setTab] = useState<ReportKey>(first);
  const previous = useRef<Set<ReportKey>>(new Set());
  const timer = useRef<number | null>(null);
  const [settling, setSettling] = useState<ReportKey | null>(null);
  useEffect(() => {
    const filed = all
      .filter((s) => !s.analyst || selectedAnalysts.includes(s.analyst))
      .filter((s) => reports[s.key])
      .map((s) => s.key);
    const added = filed.filter((key) => !previous.current.has(key));
    const finalJustFiled = added.includes("final_trade_decision");
    previous.current = new Set(filed);
    const arriving = finalJustFiled ? "final_trade_decision" : added.at(-1);
    if (arriving) {
      setTab(arriving);
      setSettling(arriving);
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        setSettling(null);
        timer.current = null;
      }, 180);
    }
  }, [reports, selectedAnalysts]);
  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );
  if (loading)
    return (
      <section className="evidence-file">
        <Skeleton className="wide" />
        <Skeleton className="wide" />
        <Skeleton className="wide" />
      </section>
    );
  return (
    <section className="evidence-file" aria-labelledby="evidence-title">
      <header>
        <span className="folio">Open evidence file</span>
        <h2 id="evidence-title">Reports assemble here</h2>
        <p>
          Illustrative workspace content appears only when test data is used.
        </p>
      </header>
      <Tabs value={tab} onValueChange={(value) => setTab(value as ReportKey)}>
        <TabsList className="report-tabs" aria-label="Evidence reports">
          {sections.map((s) => (
            <TabsTrigger
              value={s.key}
              key={s.key}
              className={reports[s.key] ? "assembled" : ""}
            >
              {s.label}
              <span className="tab-state">
                {reports[s.key] ? "Filed" : "Awaiting"}
              </span>
            </TabsTrigger>
          ))}
        </TabsList>
        {sections.map((s) => (
          <TabsContent
            value={s.key}
            key={s.key}
            className={
              reports[s.key]
                ? `report-sheet ${settling === s.key ? "assembled-sheet" : ""}`
                : "report-sheet"
            }
          >
            {reports[s.key] ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noreferrer noopener">
                      {children}
                    </a>
                  ),
                }}
              >
                {reports[s.key]}
              </ReactMarkdown>
            ) : (
              <div className="awaiting">
                <strong>{s.label} exhibit awaiting</strong>
                <p>
                  This sheet settles into the evidence stack when its
                  responsible agent completes.
                </p>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}
