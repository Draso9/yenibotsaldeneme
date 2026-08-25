"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { fetchAdminQuality } from "../lib/admin-quality";
import { useIzfinAuth } from "./auth-provider";

const navItems = [
  { icon: "⌂", label: "Piyasa Merkezi", href: "/", upcoming: false, adminOnly: false },
  { icon: "⌕", label: "Akıllı Tarama", href: "/#akilli-tarama", upcoming: false, adminOnly: false },
  { icon: "◈", label: "Projeksiyon", href: "/projection", upcoming: false, adminOnly: false },
  { icon: "◫", label: "Performans", href: "/performance", upcoming: false, adminOnly: false },
  { icon: "◇", label: "Strateji Lab", href: "/strategy-lab", upcoming: false, adminOnly: false },
  { icon: "◌", label: "Hesap", href: "/account", upcoming: false, adminOnly: false },
  { icon: "⚙", label: "Admin QA", href: "/admin/quality", upcoming: false, adminOnly: true },
] as const;

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const { user, loading, getIdToken } = useIzfinAuth();
  const pathname = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    if (loading || !user) {
      setIsAdmin(false);
      return;
    }
    let active = true;
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        await fetchAdminQuality(token);
        if (active) setIsAdmin(true);
      } catch {
        if (active) setIsAdmin(false);
      }
    })();
    return () => { active = false; };
  }, [getIdToken, loading, user]);

  const pageLabel = pathname.startsWith("/stocks/")
    ? "Detaylı Analiz"
    : pathname.startsWith("/projection")
      ? "Projeksiyon"
      : pathname.startsWith("/performance")
        ? "Performans"
        : pathname.startsWith("/strategy-lab")
          ? "Strateji Laboratuvarı"
          : pathname.startsWith("/account")
            ? "Gizlilik & Hesap"
            : pathname.startsWith("/admin/quality")
              ? "Admin QA · Sistem Sağlığı"
              : "Piyasa Merkezi";

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true"><span>I</span><span>Z</span></div>
        <div className="brand-copy"><b>IZFIN</b><span>MARKET INTELLIGENCE</span></div>
      </div>

      <div className="nav-label">ÇALIŞMA ALANI</div>
      <nav aria-label="Ana navigasyon">
        {navItems.filter((item) => !item.adminOnly || isAdmin).map((item, index) => {
          const active = item.label === "Projeksiyon"
            ? pathname.startsWith("/projection")
            : item.label === "Performans"
              ? pathname.startsWith("/performance")
              : item.label === "Strateji Lab"
                ? pathname.startsWith("/strategy-lab")
                : item.label === "Hesap"
                  ? pathname.startsWith("/account")
                  : item.label === "Admin QA"
                    ? pathname.startsWith("/admin/quality")
                    : item.label === "Piyasa Merkezi"
                      ? pathname === "/" || pathname.startsWith("/stocks/")
                      : false;
          return <a className={`${active ? "active" : ""}${item.upcoming ? " upcoming" : ""}`} href={item.href} key={`${item.label}-${index}`}>
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
