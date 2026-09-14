import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, ...p }, ref) => (
  <button ref={ref} className={cn("docket-button", className)} {...p} />
));
Button.displayName = "Button";
