import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
export const Badge = ({ className, ...p }: HTMLAttributes<HTMLSpanElement>) => (
  <span className={cn("docket-badge", className)} {...p} />
);
