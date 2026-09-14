import { InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";
export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(({ className, ...p }, ref) => (
  <input ref={ref} className={cn("docket-input", className)} {...p} />
));
Input.displayName = "Input";
