import type { ActivityMessage, AgentStatus, AnalystKey } from "@/lib/types";
const groups: [string, string[]][] = [
  [
    "Analyst team",
    [
      "Market Analyst",
      "Sentiment Analyst",
      "News Analyst",
      "Fundamentals Analyst",
    ],
  ],
  ["Research team", ["Bull Researcher", "Bear Researcher", "Research Manager"]],
  ["Trading team", ["Trader"]],
  [
    "Risk management",
    ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
  ],
  ["Portfolio management", ["Portfolio Manager"]],
];
export function AgentProgress({
  statuses,
  selectedAnalysts,
  messages,
  connection,
}: {
  statuses: Record<string, AgentStatus>;
  selectedAnalysts: AnalystKey[];
  messages: ActivityMessage[];
  connection: string;
}) {
  const allowed = (agent: string) =>
    !agent.endsWith("Analyst") ||
    ![
      "Market Analyst",
      "Sentiment Analyst",
      "News Analyst",
      "Fundamentals Analyst",
    ].includes(agent) ||
    selectedAnalysts.includes(
      (
        {
          "Market Analyst": "market",
          "Sentiment Analyst": "social",
          "News Analyst": "news",
          "Fundamentals Analyst": "fundamentals",
        } as Record<string, AnalystKey>
      )[agent],
    );
  return (
    <section className="pipeline" aria-labelledby="pipeline-title">
      <header>
        <div>
          <span className="folio">Evidence sequence</span>
          <h2 id="pipeline-title">Agent record</h2>
        </div>
        <span className={`connection ${connection}`}>
          {connection.replace("_", " ")}
        </span>
      </header>
      <div className="pipeline-grid">
        {groups.map(([team, agents]) => {
          const visibleAgents = agents.filter(allowed);
          const waitingOnModel = visibleAgents.some(
            (agent) => statuses[agent] === "in_progress",
          );
          return (
            <div
              className="team"
              data-active={waitingOnModel || undefined}
              key={team}
            >
              <div className="team-heading">
                <h3>{team}</h3>
                {waitingOnModel && (
                  <span
                    className="model-wait"
                    role="status"
                    aria-label={`${team} awaiting model response`}
                  >
                    <span className="model-wait-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span>Awaiting model</span>
                  </span>
                )}
              </div>
              {visibleAgents.map((agent) => {
                const state = statuses[agent] || "pending";
                return (
                  <div className="agent" data-status={state} key={agent}>
                    <span aria-hidden="true" />
                    <b>{agent}</b>
                    <em>{state.replace("_", " ")}</em>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
      <ol
        className="activity"
        aria-label="Activity record"
        aria-live="polite"
        aria-relevant="additions"
      >
        {messages.length ? (
          messages.map((m, i) => (
            <li key={m.id || i}>
              <b>{m.source || m.category}</b>
              <span>
                {(m.stage || m.emittedAt) && (
                  <small>
                    {[
                      m.stage,
                      m.emittedAt &&
                        new Date(m.emittedAt).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        }),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </small>
                )}
                {m.content}
              </span>
            </li>
          ))
        ) : (
          <li className="activity-empty">
            Events from the selected analysts will be recorded here.
          </li>
        )}
      </ol>
    </section>
  );
}
