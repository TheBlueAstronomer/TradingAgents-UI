import { InputHTMLAttributes, forwardRef } from "react";
export const Checkbox = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>((p, ref) => <input ref={ref} type="checkbox" {...p} />);
Checkbox.displayName = "Checkbox";
