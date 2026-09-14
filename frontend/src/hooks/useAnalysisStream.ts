"use client";
import { useEffect, useRef, useState } from "react";
import { getAnalysis } from "@/lib/api";
import type { ActivityMessage, AnalysisDetail, StreamEvent } from "@/lib/types";
export interface AnalysisStreamState {
  run: AnalysisDetail | null;
  connection: "idle" | "connecting" | "open" | "reconnecting" | "closed";
  messages: ActivityMessage[];
  error: string | null;
}
export function useAnalysisStream(runId: string): AnalysisStreamState {
  const [state, setState] = useState<AnalysisStreamState>({
    run: null,
    connection: "idle",
    messages: [],
    error: null,
  });
  const seq = useRef(0);
  const terminal = useRef(false);
  useEffect(() => {
    seq.current = 0;
    terminal.current = false;
    let stopped = false,
      socket: WebSocket | undefined,
      timer: number | undefined,
      attempt = 0;
    const controller = new AbortController();
    const apply = (event: StreamEvent) => {
      if (event.seq <= seq.current) return;
      seq.current = event.seq;
      const eventRun = event.data.run as AnalysisDetail | undefined;
      const terminalEvent = ["complete", "error"].includes(event.type);
      const terminalSnapshot =
        eventRun?.status === "completed" || eventRun?.status === "failed";
      if (terminalEvent || terminalSnapshot) terminal.current = true;
      setState((old) => {
        let run = old.run;
        let messages = old.messages;
        if (
          eventRun &&
          ["snapshot", "complete", "error"].includes(event.type)
        )
          run = eventRun;
        if (event.type === "status" && run)
          run = {
            ...run,
            status: event.data.status as AnalysisDetail["status"],
          };
        if (event.type === "report" && run)
          run = {
            ...run,
            reports: {
              ...run.reports,
              [event.data.key as string]: event.data.markdown as string,
            },
          };
        if (event.type === "agent_status" && run)
          run = {
            ...run,
            agent_statuses: {
              ...run.agent_statuses,
              [event.data.agent as string]: event.data
                .status as AnalysisDetail["agent_statuses"][string],
            },
          };
        if (event.type === "message")
          messages = [
            ...old.messages,
            {
              id: event.data.messageId as string | undefined,
              category: event.data.category as ActivityMessage["category"],
              content: event.data.content as string,
              source: event.data.source as string | undefined,
              stage: event.data.stage as string | undefined,
              emittedAt: event.emitted_at,
            },
          ].slice(-100);
        return {
          ...old,
          run,
          messages,
          connection: terminalEvent || terminalSnapshot
            ? "closed"
            : old.connection,
          error:
            event.type === "error" ? String(event.data.message) : old.error,
        };
      });
    };
    const connect = () => {
      if (stopped) return;
      setState((s) => ({
        ...s,
        connection: attempt ? "reconnecting" : "connecting",
      }));
      const url =
        (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000").replace(
          /\/$/,
          "",
        ) + `/ws/analysis/${runId}?after=${seq.current}`;
      socket = new WebSocket(url);
      socket.onopen = () => {
        attempt = 0;
        setState((s) => ({
          ...s,
          connection: "open",
          // A successful reconnect resolves only the transient transport note.
          error: terminal.current ? s.error : null,
        }));
      };
      socket.onmessage = (e) => apply(JSON.parse(e.data));
      socket.onclose = () => {
        if (stopped || terminal.current) return;
        const delay = Math.min(30000, 500 * 2 ** Math.min(attempt, 6));
        attempt++;
        timer = window.setTimeout(connect, delay);
      };
      socket.onerror = () =>
        setState((s) => ({ ...s, error: "Connection interrupted; retrying." }));
    };
    getAnalysis(runId, controller.signal)
      .then((run) => {
        if (!stopped) {
          const isTerminal =
            run.status === "completed" || run.status === "failed";
          terminal.current = isTerminal;
          seq.current = run.last_event_seq;
          setState((s) => ({
            ...s,
            run,
            connection: isTerminal ? "closed" : s.connection,
            error:
              run.status === "failed"
                ? run.error_message || "Analysis failed."
                : s.error,
          }));
          if (!isTerminal) connect();
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setState((s) => ({
            ...s,
            error: "Could not load this analysis.",
            connection: "closed",
          }));
        }
      });
    return () => {
      stopped = true;
      controller.abort();
      if (timer) clearTimeout(timer);
      socket?.close();
    };
  }, [runId]);
  return state;
}
