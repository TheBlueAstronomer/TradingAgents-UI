import { SelectHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";
export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(({ className, ...p }, ref) => (
  <select ref={ref} className={cn("docket-input", className)} {...p} />
));
Select.displayName = "Select";
