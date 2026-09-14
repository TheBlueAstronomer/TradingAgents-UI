import { TableHTMLAttributes } from "react";
export const Table = (p: TableHTMLAttributes<HTMLTableElement>) => (
  <table className="docket-table" {...p} />
);
