import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { AnalysisForm } from "../AnalysisForm";
import { ApiClientError } from "@/lib/api";
import type {
  AnalysisSummary,
  AnalystOption,
  ProviderOption,
} from "@/lib/types";

const { createAnalysis } = vi.hoisted(() => ({ createAnalysis: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  createAnalysis,
}));

const providers: ProviderOption[] = [
  {
    id: "openai",
    label: "OpenAI",
    quick_models: [{ label: "Quick", value: "quick" }],
    deep_models: [{ label: "Deep", value: "deep" }],
    allows_custom_model: false,
    requires_backend_url: false,
    default_quick_model: "quick",
    default_deep_model: "deep",
  },
];
const analysts: AnalystOption[] = [
  {
    id: "market",
    label: "Market",
    description: "Price evidence",
    selected_by_default: true,
  },
];

const compatible: ProviderOption = {
  id: "openai_compatible",
  label: "Compatible",
  quick_models: [{ label: "Custom", value: "custom" }],
  deep_models: [{ label: "Custom", value: "custom" }],
  allows_custom_model: true,
  requires_backend_url: true,
  default_quick_model: "custom",
  default_deep_model: "custom",
};
beforeEach(() => createAnalysis.mockReset());

test("initializes asynchronous configuration before it enables submission", async () => {
  const { rerender } = render(<AnalysisForm providers={[]} analysts={[]} />);
  expect(
    screen.getByRole("button", { name: /loading configuration/i }),
  ).toBeDisabled();
  rerender(<AnalysisForm providers={providers} analysts={analysts} />);
  await waitFor(() =>
    expect(screen.getByLabelText(/provider/i)).toHaveValue("openai"),
  );
  fireEvent.change(screen.getByLabelText(/ticker/i), {
    target: { value: "aapl" },
  });
  fireEvent.change(screen.getByLabelText(/analysis date/i), {
    target: { value: "2026-09-14" },
  });
  fireEvent.change(screen.getByLabelText(/quick model/i), {
    target: { value: "quick" },
  });
  fireEvent.change(screen.getByLabelText(/deep model/i), {
    target: { value: "deep" },
  });
  const market = screen.getByRole("checkbox", { name: /market/i });
  if (!market.checked) fireEvent.click(market);
  expect(screen.getByLabelText(/quick model/i)).toHaveValue("quick");
  expect(screen.getByLabelText(/deep model/i)).toHaveValue("deep");
  expect(market).toBeChecked();
  expect(screen.getByRole("button", { name: /start analysis/i })).toBeEnabled();
});

test("resets models to the newly selected provider defaults", async () => {
  const alternate = {
    ...providers[0],
    id: "alternate",
    label: "Alternate",
    quick_models: [{ label: "Alt quick", value: "alt-q" }],
    deep_models: [{ label: "Alt deep", value: "alt-d" }],
    default_quick_model: "alt-q",
    default_deep_model: "alt-d",
  };
  render(
    <AnalysisForm providers={[providers[0], alternate]} analysts={analysts} />,
  );
  await waitFor(() =>
    expect(screen.getByLabelText(/provider/i)).toHaveValue("openai"),
  );
  fireEvent.change(screen.getByLabelText(/provider/i), {
    target: { value: "alternate" },
  });
  await waitFor(() =>
    expect(screen.getByLabelText(/quick model/i)).toHaveValue("alt-q"),
  );
  expect(screen.getByLabelText(/deep model/i)).toHaveValue("alt-d");
});

test("submits normalized data and reports the created run", async () => {
  const created = { id: "run-1" } as never;
  createAnalysis.mockResolvedValueOnce(created);
  const onCreated = vi.fn();
  render(
    <AnalysisForm
      providers={providers}
      analysts={analysts}
      onCreated={onCreated}
    />,
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: /start analysis/i }),
    ).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText(/ticker/i), {
    target: { value: "aapl" },
  });
  fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
  await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
  expect(createAnalysis).toHaveBeenCalledTimes(1);
  expect(createAnalysis).toHaveBeenCalledWith(
    expect.objectContaining({
      ticker: "AAPL",
      analysts: ["market"],
      llm_provider: "openai",
      quick_think_llm: "quick",
      deep_think_llm: "deep",
    }),
  );
});

test("disables submission while pending and prevents a double submit", async () => {
  const created = { id: "run-1" } as AnalysisSummary;
  let resolveRequest!: (value: AnalysisSummary) => void;
  createAnalysis.mockReturnValueOnce(
    new Promise<AnalysisSummary>((resolve) => {
      resolveRequest = resolve;
    }),
  );
  const onCreated = vi.fn();
  render(
    <AnalysisForm
      providers={providers}
      analysts={analysts}
      onCreated={onCreated}
    />,
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: /start analysis/i }),
    ).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText(/ticker/i), {
    target: { value: "aapl" },
  });
  fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));

  const pending = await screen.findByRole("button", {
    name: /opening docket/i,
  });
  expect(pending).toBeDisabled();
  expect(pending).toHaveAttribute("aria-busy", "true");
  fireEvent.click(pending);
  expect(createAnalysis).toHaveBeenCalledTimes(1);

  resolveRequest(created);
  await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
});

test("shows a structured API failure without clearing entered values", async () => {
  createAnalysis.mockRejectedValueOnce(
    new ApiClientError(
      422,
      "INVALID_MODEL",
      "Model is incompatible with provider",
      "quick_think_llm",
    ),
  );
  const onCreated = vi.fn();
  render(
    <AnalysisForm
      providers={providers}
      analysts={analysts}
      onCreated={onCreated}
    />,
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: /start analysis/i }),
    ).toBeEnabled(),
  );
  const ticker = screen.getByLabelText(/ticker/i);
  fireEvent.change(ticker, { target: { value: "aapl" } });
  fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Model is incompatible with provider",
  );
  expect(ticker).toHaveValue("aapl");
  expect(onCreated).not.toHaveBeenCalled();
});

test("custom-compatible providers require a real model id as well as backend URL", async () => {
  render(<AnalysisForm providers={[compatible]} analysts={analysts} />);
  await waitFor(() =>
    expect(screen.getByLabelText(/provider/i)).toHaveValue("openai_compatible"),
  );
  expect(screen.getByLabelText(/compatible backend url/i)).toBeRequired();
  expect(screen.getByLabelText(/quick custom model/i)).toBeRequired();
  expect(screen.getByLabelText(/deep custom model/i)).toBeRequired();
});
