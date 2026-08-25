"use client";

import { useIzfinAuth } from "./auth-provider";

const navItems = [
  ["⌂", "Ana Sayfa"], ["⌕", "Akıllı Tarama"], ["◈", "Projeksiyon"], ["◫", "Performans"], ["◌", "Hesap"],
] as const;

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const { user } = useIzfinAuth();
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">IZ</div><div><b>IZFIN</b><span>ANALYZE • PREDICT • INVEST</span></div></div>
      <nav>{navItems.map(([icon, label], index) => <a className={index === 0 ? "active" : ""} href={index === 0 ? "#top" : `#${label.toLocaleLowerCase("tr-TR").replaceAll(" ", "-")}`} key={label}><i>{icon}</i>{label}</a>)}</nav>
      <div className="sidebar-footer"><span className="live-dot" /> Sistemler hazır<br />{user?.email ?? "Güvenli oturum"}</div>
    </aside>
    <div className="app-content"><header className="topbar"><span>IZFIN SIGNATURE COMMAND CENTER</span><div><span className="market-open">● API CANLI</span><span className="top-time">WEB BETA</span></div></header>{children}</div>
  </div>;
}
