import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { SignalBadge } from "../SignalBadge";
test("labels review", () => {
  render(<SignalBadge signal="REVIEW" />);
  expect(screen.getByText("REVIEW")).toBeInTheDocument();
});

test.each(["BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL", "REVIEW"] as const)("renders %s with accessible signal text", (signal) => {
  render(<SignalBadge signal={signal} size="md" />);
  expect(screen.getByText(signal)).toBeInTheDocument();
  expect(screen.getByText(signal)).toHaveClass(`signal-${signal.toLowerCase()}`, "md");
});

test("renders a null signal without pretending a decision exists", () => {
  render(<SignalBadge signal={null} />);
  expect(screen.getByText(/no signal/i)).toBeInTheDocument();
});
