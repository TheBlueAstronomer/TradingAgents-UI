import { LabelHTMLAttributes } from "react";
export function Label(p: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className="docket-label" {...p} />;
}
