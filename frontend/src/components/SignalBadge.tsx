import { Badge } from "@/components/ui/badge";
import type { Signal } from "@/lib/types";
export function SignalBadge({
  signal,
  size = "sm",
}: {
  signal: Signal | null;
  size?: "sm" | "md";
}) {
  return (
    <Badge
      className={`signal signal-${signal?.toLowerCase() || "none"} ${size}`}
    >
      {signal || "No signal"}
      <span className="sr-only"> signal</span>
    </Badge>
  );
}
