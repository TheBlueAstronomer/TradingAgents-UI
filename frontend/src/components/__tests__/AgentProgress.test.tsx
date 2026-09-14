import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { AgentProgress } from "../AgentProgress";
test("omits unselected analysts", () => {
  render(
    <AgentProgress
      statuses={{}}
      selectedAnalysts={["market"]}
      messages={[]}
      connection="open"
    />,
  );
  expect(screen.getByText("Market Analyst")).toBeInTheDocument();
  expect(screen.queryByText("News Analyst")).toBeNull();
});

test("announces connection, agent state, and activity through an accessible live log", () => {
  render(
    <AgentProgress
      statuses={{ "Market Analyst": "in_progress", Trader: "completed" }}
      selectedAnalysts={["market"]}
      connection="reconnecting"
      messages={[
        {
          id: "m1",
          category: "Agent",
          content: "Evidence received",
          stage: "Market",
        },
      ]}
    />,
  );
  expect(screen.getByText("reconnecting")).toBeInTheDocument();
  expect(screen.getByText("in progress")).toBeInTheDocument();
  expect(
    screen.getByRole("status", { name: /analyst team awaiting model response/i }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("list", { name: /activity record/i }),
  ).toHaveAttribute("aria-live", "polite");
  expect(screen.getByText("Evidence received")).toBeInTheDocument();
});
