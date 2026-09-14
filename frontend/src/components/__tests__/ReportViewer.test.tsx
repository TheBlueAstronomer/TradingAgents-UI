import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ReportViewer } from "../ReportViewer";

afterEach(() => vi.useRealTimers());
test("does not render raw html", () => {
  render(
    <ReportViewer
      loading={false}
      selectedAnalysts={["market"]}
      reports={{ market_report: "<script>bad</script>" }}
    />,
  );
  expect(screen.queryByRole("script")).toBeNull();
  expect(screen.getByText("<script>bad</script>")).toBeInTheDocument();
});

test("uses GFM and excludes reports for unselected analysts", () => {
  render(<ReportViewer loading={false} selectedAnalysts={["market"]} reports={{ market_report: "| Evidence | Value |\n| --- | --- |\n| A | B |", news_report: "must not appear" }} />);
  expect(screen.getByRole("table")).toBeInTheDocument();
  expect(screen.queryByRole("tab", { name: /news/i })).toBeNull();
  expect(screen.getByRole("tab", { name: /market filed/i })).toBeInTheDocument();
});

test("supports keyboard report-tab navigation in report order", () => {
  render(<ReportViewer loading={false} selectedAnalysts={["market", "social"]} reports={{ market_report: "M", sentiment_report: "S" }} />);
  const market = screen.getByRole("tab", { name: /market filed/i });
  market.focus();
  fireEvent.keyDown(market, { key: "ArrowRight" });
  expect(screen.getByRole("tab", { name: /sentiment filed/i })).toHaveAttribute("aria-selected", "true");
});

test("activates only the newest arriving report and settles it once", () => {
  vi.useFakeTimers();
  const { container, rerender } = render(
    <ReportViewer
      loading={false}
      selectedAnalysts={["market", "social"]}
      reports={{}}
    />,
  );
  rerender(
    <ReportViewer
      loading={false}
      selectedAnalysts={["market", "social"]}
      reports={{ market_report: "Market", sentiment_report: "Sentiment" }}
    />,
  );
  expect(screen.getByRole("tab", { name: /sentiment filed/i })).toHaveAttribute(
    "data-state",
    "active",
  );
  expect(
    container.querySelector('.report-sheet[data-state="active"]'),
  ).toHaveClass("assembled-sheet");
  act(() => vi.advanceTimersByTime(180));
  expect(
    container.querySelector('.report-sheet[data-state="active"]'),
  ).not.toHaveClass("assembled-sheet");
  fireEvent.click(
    container.querySelector('[role="tab"][aria-controls$="market_report"]')!,
  );
  expect(
    container.querySelector('.report-sheet[data-state="active"]'),
  ).not.toHaveClass("assembled-sheet");
  rerender(
    <ReportViewer
      loading={false}
      selectedAnalysts={["market", "social"]}
      reports={{
        market_report: "Market",
        sentiment_report: "Sentiment",
        final_trade_decision: "Final memorandum",
      }}
    />,
  );
  expect(
    screen.getByRole("tab", { name: /final memorandum filed/i }),
  ).toHaveAttribute("data-state", "active");
});
