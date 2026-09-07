"use client";

import { usePathname, useSearchParams } from "next/navigation";

// Isolated under Suspense so reading this contextual query does not suspend the shell.
export function StockDetailNavLink() {
  const pathname = usePathname();
  const query = useSearchParams().toString();
  const href = query ? `${pathname}?${query}` : pathname;
  return <a aria-current="page" className="active contextual-nav-item" href={href}>
    <i aria-hidden="true">◎</i><span>Detaylı Analiz</span><em>BAĞLAM</em>
  </a>;
}
