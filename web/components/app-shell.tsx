"use client";

import { usePathname } from "next/navigation";
import { useIzfinAuth } from "./auth-provider";

const navItems = [
  { icon: "⌂", label: "Piyasa Merkezi", href: "/", upcoming: false },
  { icon: "⌕", label: "Akıllı Tarama", href: "/#akilli-tarama", upcoming: false },
  { icon: "◈", label: "Projeksiyon", href: "/#projeksiyon", upcoming: true },
  { icon: "◫", label: "Performans", href: "/#performans", upcoming: true },
  { icon: "◌", label: "Hesap", href: "/#hesap", upcoming: false },
] as const;

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const { user } = useIzfinAuth();
  const pathname = usePathname();
  const pageLabel = pathname.startsWith("/stocks/") ? "Detaylı Analiz" : "Piyasa Merkezi";

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true"><span>I</span><span>Z</span></div>
        <div className="brand-copy"><b>IZFIN</b><span>MARKET INTELLIGENCE</span></div>
      </div>

      <div className="nav-label">ÇALIŞMA ALANI</div>
      <nav aria-label="Ana navigasyon">
        {navItems.map((item, index) => {
          const active = pathname === "/" ? index === 0 : pathname.startsWith("/stocks/") && index === 0;
          return <a className={`${active ? "active" : ""}${item.upcoming ? " upcoming" : ""}`} href={item.href} key={item.label}>
            <i aria-hidden="true">{item.icon}</i>
            <span>{item.label}</span>
            {item.upcoming && <em>yakında</em>}
          </a>;
        })}
      </nav>

      <div className="sidebar-spacer" />
      <div className="sidebar-status">
        <div className="system-line"><span className="live-dot" /><strong>Sistemler hazır</strong></div>
        <span className="sidebar-meta">FastAPI · Next.js · güvenli oturum</span>
        <span className="sidebar-user">{user?.email ?? "Oturum bekleniyor"}</span>
      </div>
    </aside>

    <div className="app-content">
      <header className="topbar">
        <div className="topbar-title"><span>IZFIN</span><b>{pageLabel}</b></div>
        <div className="topbar-actions">
          <span className="environment-chip">WEB BETA</span>
          <span className="api-chip"><i className="live-dot" /> API CANLI</span>
        </div>
      </header>
      {children}
    </div>
  </div>;
}
