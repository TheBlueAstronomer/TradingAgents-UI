import { expect, test, type Page } from "@playwright/test";
import type {
  AnalysisDetail,
  AnalysisSummary,
  HistoryPage,
  Signal,
  StreamEvent,
} from "../src/lib/types";

const run: AnalysisDetail = {
  id: "test-run-1",
  ticker: "SYNTH-AAPL",
  analysis_date: "2025-01-01",
  asset_type: "stock",
  analysts: ["market"],
  llm_provider: "openai",
  research_depth: 1,
  status: "queued",
  signal: null,
  created_at: "2025-01-01T00:00:00Z",
  started_at: null,
  completed_at: null,
  quick_think_llm: "quick",
  deep_think_llm: "deep",
  reports: {},
  agent_statuses: { "Market Analyst": "pending" },
  error_message: null,
  final_state: null,
  last_event_seq: 0,
};
const providers = [
  {
    id: "openai",
    label: "OpenAI test data",
    quick_models: [{ label: "Quick", value: "quick" }],
    deep_models: [{ label: "Deep", value: "deep" }],
    allows_custom_model: false,
    requires_backend_url: false,
    default_quick_model: "quick",
    default_deep_model: "deep",
  },
];
const analysts = [
  {
    id: "market" as const,
    label: "Market test analyst",
    description: "Test evidence",
    selected_by_default: true,
  },
];
const signals: Signal[] = [
  "BUY",
  "OVERWEIGHT",
  "HOLD",
  "UNDERWEIGHT",
  "SELL",
  "REVIEW",
];
const streamedMarkdown =
  "## Verified evidence\n\n<script>window.__e2e_injected = true</script>\n\n[Trusted source](https://example.test/evidence)";

function summary(
  id: string,
  ticker: string,
  signal: Signal,
  index: number,
): AnalysisSummary {
  return {
    ...run,
    id,
    ticker,
    status: "completed",
    signal,
    created_at: "2025-01-" + String(index + 1).padStart(2, "0") + "T00:00:00Z",
  };
}

const historyRuns: AnalysisSummary[] = [
  ...signals.map((signal, index) =>
    summary("signal-" + index, "SIG" + index, signal, index + 15),
  ),
  ...Array.from({ length: 15 }, (_, index) =>
    summary(
      "filler-" + index,
      "FILL" + String(index).padStart(2, "0"),
      "REVIEW",
      index,
    ),
  ),
];

function event(
  seq: number,
  type: string,
  data: Record<string, unknown>,
): StreamEvent {
  return {
    run_id: run.id,
    seq,
    emitted_at: "2025-01-01T00:00:0" + Math.min(seq, 9) + "Z",
    type,
    data,
  };
}

async function mockDashboard(page: Page) {
  await page.route("**/api/config/providers", (route) =>
    route.fulfill({ json: providers }),
  );
  await page.route("**/api/config/analysts", (route) =>
    route.fulfill({ json: analysts }),
  );
  await page.route("**/api/history**", (route) =>
    route.fulfill({
      json: { items: [], total: 0, page: 1, page_size: 5 },
    }),
  );
}

function sortedHistory(url: URL): HistoryPage {
  const ticker = url.searchParams.get("ticker") || "";
  const page = Number(url.searchParams.get("page") || "1");
  const pageSize = Number(url.searchParams.get("page_size") || "20");
  const sortBy = (url.searchParams.get("sort_by") ||
    "created_at") as keyof AnalysisSummary;
  const descending = url.searchParams.get("sort_order") !== "asc";
  const filtered = historyRuns
    .filter((item) => item.ticker.includes(ticker.toUpperCase()))
    .sort((left, right) => {
      const order = String(left[sortBy] ?? "").localeCompare(
        String(right[sortBy] ?? ""),
      );
      return descending ? -order : order;
    });
  return {
    items: filtered.slice((page - 1) * pageSize, page * pageSize),
    total: filtered.length,
    page,
    page_size: pageSize,
  };
}

async function expectNoHorizontalOverflow(page: Page) {
  const viewportWidth = page.viewportSize()?.width;
  await expect
    .poll(() =>
      page.locator("html").evaluate((element) => ({
        clientWidth: element.clientWidth,
        scrollWidth: element.scrollWidth,
      })),
    )
    .toEqual({ clientWidth: viewportWidth, scrollWidth: viewportWidth });
}

test("dashboard submits normalized mocked data with keyboard-only controls", async ({
  page,
}) => {
  let submitted: unknown;
  await mockDashboard(page);
  await page.route("**/api/analysis", async (route) => {
    submitted = route.request().postDataJSON();
    await route.fulfill({ status: 202, json: run });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /open an analysis/i }),
  ).toBeVisible();
  await page.getByLabel("Ticker").focus();
  await page.keyboard.type("synth-aapl");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/analysis\/test-run-1$/);
  expect(submitted).toMatchObject({
    ticker: "SYNTH-AAPL",
    analysts: ["market"],
    llm_provider: "openai",
    quick_think_llm: "quick",
    deep_think_llm: "deep",
  });
});

test("dashboard presents active work and the latest real filing", async ({ page }) => {
  const active = {
    ...run,
    id: "active-run",
    ticker: "LIVE-AME",
    status: "running" as const,
    started_at: "2025-01-20T00:01:00Z",
  };
  const filed = {
    ...run,
    id: "filed-run",
    ticker: "FILED-MP",
    status: "completed" as const,
    signal: "HOLD" as const,
    completed_at: "2025-01-20T00:10:00Z",
  };
  await page.route("**/api/config/providers", (route) =>
    route.fulfill({ json: providers }),
  );
  await page.route("**/api/config/analysts", (route) =>
    route.fulfill({ json: analysts }),
  );
  await page.route("**/api/history**", (route) => {
    const status = new URL(route.request().url()).searchParams.get("status");
    const items =
      status === "running"
        ? [active]
        : status === "queued"
          ? []
          : status === "completed"
            ? [filed]
            : [active, filed];
    return route.fulfill({
      json: { items, total: items.length, page: 1, page_size: 5 },
    });
  });
  await page.route("**/api/analysis/filed-run", (route) =>
    route.fulfill({
      json: {
        ...filed,
        reports: {
          final_trade_decision:
            "## Final memorandum\n\nVerified conclusion from the completed docket.",
        },
      },
    }),
  );

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Active dockets" })).toBeVisible();
  await expect(page.getByText("LIVE-AME", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Latest filing" })).toBeVisible();
  await expect(page.getByText(/verified conclusion from the completed docket/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /open full dossier/i })).toHaveAttribute(
    "href",
    "/analysis/filed-run",
  );
});

test("analysis progresses through reconnect to a completed, safe report", async ({
  page,
}) => {
  const socketUrls: string[] = [];
  let socketCount = 0;
  let releaseReconnect = () => {};
  const reconnectGate = new Promise<void>((resolve) => {
    releaseReconnect = resolve;
  });
  const completed: AnalysisDetail = {
    ...run,
    status: "completed",
    signal: "BUY",
    started_at: "2025-01-01T00:00:01Z",
    completed_at: "2025-01-01T00:00:07Z",
    reports: { market_report: streamedMarkdown },
    agent_statuses: { "Market Analyst": "completed" },
    final_state: { final_trade_decision: "BUY" },
    last_event_seq: 7,
  };

  await page.route("**/api/analysis/test-run-1", (route) =>
    route.fulfill({ json: run }),
  );
  await page.routeWebSocket(
    "**/ws/analysis/test-run-1?after=*",
    async (socket) => {
      socketCount += 1;
      socketUrls.push(socket.url());
      if (socketCount === 1) {
        setTimeout(() => {
          socket.send(
            JSON.stringify(event(1, "status", { status: "running" })),
          );
          socket.send(
            JSON.stringify(
              event(2, "agent_status", {
                agent: "Market Analyst",
                team: "Analyst Team",
                status: "in_progress",
              }),
            ),
          );
        }, 25);
        setTimeout(() => {
          void socket.close({
            code: 1012,
            reason: "deterministic test restart",
          });
        }, 250);
        return;
      }

      await reconnectGate;
      setTimeout(() => {
        socket.send(
          JSON.stringify(
            event(3, "message", {
              messageId: "evidence-1",
              category: "Agent",
              content: "Evidence assembled",
            }),
          ),
        );
        socket.send(
          JSON.stringify(
            event(4, "report", {
              key: "market_report",
              title: "Market analysis",
              markdown: streamedMarkdown,
            }),
          ),
        );
        socket.send(
          JSON.stringify(
            event(5, "agent_status", {
              agent: "Market Analyst",
              team: "Analyst Team",
              status: "completed",
            }),
          ),
        );
        socket.send(JSON.stringify(event(6, "signal", { signal: "BUY" })));
        socket.send(JSON.stringify(event(7, "complete", { run: completed })));
        void socket.close({ code: 1000, reason: "complete" });
      }, 25);
    },
  );

  await page.goto("/analysis/test-run-1");
  await expect(
    page.getByRole("heading", { name: /synth-aapl research record/i }),
  ).toBeVisible();
  await expect(page.locator(".status-stamp")).toHaveText("running");
  await expect(
    page.locator('.agent:has-text("Market Analyst")'),
  ).toHaveAttribute("data-status", "in_progress");

  await expect.poll(() => socketCount).toBe(2);
  await expect(page.locator(".connection.reconnecting")).toBeVisible();
  expect(socketUrls[1]).toContain("?after=2");
  releaseReconnect();

  await expect(page.locator(".status-stamp")).toHaveText("completed");
  await expect(page.locator(".signal-buy")).toContainText("BUY");
  await expect(page.locator(".connection.closed")).toBeVisible();
  await expect(page.getByText("Evidence assembled")).toBeVisible();
  await expect(
    page.getByText("<script>window.__e2e_injected = true</script>"),
  ).toBeVisible();
  await expect(
    page.locator("script").filter({ hasText: "__e2e_injected" }),
  ).toHaveCount(0);
  expect(await page.evaluate(() => Reflect.get(window, "__e2e_injected"))).toBe(
    undefined,
  );
  await expect(
    page.getByRole("link", { name: "Trusted source" }),
  ).toHaveAttribute("rel", "noreferrer noopener");

  const marketTab = page.getByRole("tab", { name: /market filed/i });
  await marketTab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: /research awaiting/i }),
  ).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("ArrowLeft");
  await expect(marketTab).toHaveAttribute("aria-selected", "true");
});

test("history proves signals, sorting, pagination, empty filtering, and failure", async ({
  page,
}) => {
  const requests: string[] = [];
  await page.route("**/api/history**", async (route) => {
    const url = new URL(route.request().url());
    requests.push(url.search);
    if (url.searchParams.get("ticker") === "FAIL") {
      await route.fulfill({
        status: 500,
        json: { detail: { code: "TEST", message: "test failure" } },
      });
      return;
    }
    await route.fulfill({ json: sortedHistory(url) });
  });

  await page.goto("/history");
  await expect(page.locator("tbody tr")).toHaveCount(20);
  for (const signal of signals) {
    await expect(
      page.locator(".signal-" + signal.toLowerCase()).first(),
    ).toContainText(signal);
  }

  await page.getByRole("button", { name: /^ticker/i }).click();
  await expect
    .poll(() =>
      requests.some(
        (request) =>
          request.includes("sort_by=ticker") &&
          request.includes("sort_order=desc") &&
          request.includes("page=1"),
      ),
    )
    .toBe(true);
  await expect(
    page.locator("tbody tr").first().locator("td").first(),
  ).toHaveText("SIG5");

  await page.getByRole("button", { name: /next/i }).click();
  await expect
    .poll(() => requests.some((request) => request.includes("page=2")))
    .toBe(true);
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.getByText("FILL00", { exact: true })).toBeVisible();

  await page.getByLabel(/filter by ticker/i).fill("EMPTY");
  await expect(page.getByText(/no dockets filed yet/i)).toBeVisible();

  await page.getByLabel(/filter by ticker/i).fill("FAIL");
  await expect(
    page.getByText(/could not retrieve the docket index/i),
  ).toBeVisible();
});

for (const width of [390, 768, 1280, 1440]) {
  test(
    "dashboard, analysis, and history have no horizontal overflow at " +
      width +
      "px",
    async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.route("**/api/config/providers", (route) =>
        route.fulfill({ json: providers }),
      );
      await page.route("**/api/config/analysts", (route) =>
        route.fulfill({ json: analysts }),
      );
      await page.route("**/api/history**", (route) =>
        route.fulfill({
          json: {
            items: historyRuns.slice(0, 6),
            total: 6,
            page: 1,
            page_size: 20,
          },
        }),
      );
      await page.route("**/api/analysis/test-run-1", (route) =>
        route.fulfill({
          json: {
            ...run,
            status: "completed",
            signal: "BUY",
            reports: { market_report: "## Complete" },
            last_event_seq: 3,
          },
        }),
      );
      await page.routeWebSocket("**/ws/analysis/test-run-1?after=*", () => {});

      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: /open an analysis/i }),
      ).toBeVisible();
      await expectNoHorizontalOverflow(page);

      await page.goto("/analysis/test-run-1");
      await expect(
        page.getByRole("heading", { name: /synth-aapl research record/i }),
      ).toBeVisible();
      await expectNoHorizontalOverflow(page);

      await page.goto("/history");
      await expect(page.getByText("SIG0", { exact: true })).toBeVisible();
      await expectNoHorizontalOverflow(page);
    },
  );
}
