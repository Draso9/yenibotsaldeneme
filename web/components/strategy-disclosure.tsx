import type { ReactNode } from "react";

export function StrategyDisclosure({
  label,
  count,
  children,
}: Readonly<{ label: string; count?: number; children: ReactNode }>) {
  return <details className="strategy-disclosure">
    <summary><span>{label}</span>{count === undefined ? null : <small>{count} kayıt</small>}</summary>
    <div className="strategy-disclosure-body">{children}</div>
  </details>;
}
