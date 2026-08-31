"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { fetchAdminQuality } from "../lib/admin-quality";
import { fetchSystemReadiness } from "../lib/system-health";
import { useIzfinAuth } from "./auth-provider";
import { IzfinBrandMark } from "./izfin-brand-mark";
import { UsageGuide } from "./usage-guide";

const navItems = [
  { icon: "⌂", label: "Piyasa Merkezi", href: "/", adminOnly: false },
  { icon: "⌕", label: "Akıllı Tarama", href: "/scan", adminOnly: false },
  { icon: "◈", label: "Projeksiyon", href: "/projection", adminOnly: false },
  { icon: "◫", label: "Performans", href: "/performance", adminOnly: false },
  { icon: "◇", label: "Strateji Lab", href: "/strategy-lab", adminOnly: false },
  { icon: "◌", label: "Hesap", href: "/account", adminOnly: false },
  { icon: "⚙", label: "Admin QA", href: "/admin/quality", adminOnly: true },
] as const;

type SystemState = "checking" | "ready" | "degraded" | "unavailable";

const systemCopy: Record<SystemState, { system: string; api: string }> = {
  checking: { system: "Sistem kontrol ediliyor", api: "API KONTROL" },
  ready: { system: "Sistemler hazır", api: "API HAZIR" },
  degraded: { system: "Sistem kısıtlı", api: "API KISITLI" },
  unavailable: { system: "Sistem durumu alınamadı", api: "API DURUMU" },
};

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const { user, loading, getIdToken } = useIzfinAuth();
  const pathname = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);
  const [systemState, setSystemState] = useState<SystemState>("checking");

  useEffect(() => {
    if (pathname.startsWith("/auth")) return;
    let active = true;
    const checkReadiness = async () => {
      try {
        const readiness = await fetchSystemReadiness();
        if (active) setSystemState(readiness.ready ? "ready" : "degraded");
      } catch {
        if (active) setSystemState("unavailable");
      }
    };
    void checkReadiness();
    const interval = window.setInterval(() => void checkReadiness(), 60_000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [pathname]);

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
    : pathname.startsWith("/scan")
      ? "Akıllı Tarama"
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

  if (pathname.startsWith("/auth")) return <>{children}</>;

  const statusCopy = systemCopy[systemState];

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Ana içeriğe geç</a>
    <aside className="sidebar">
      <div className="brand">
        <IzfinBrandMark className="sidebar-brand-mark" imageSize={52} priority />
        <div className="brand-copy"><b>IZFIN</b><span>ANALYZE · PREDICT · INVEST</span></div>
      </div>
      <div className="nav-label">ÇALIŞMA ALANI</div>
      <nav aria-label="Ana navigasyon">
        {navItems.filter((item) => !item.adminOnly || isAdmin).map((item, index) => {
          const active = item.label === "Akıllı Tarama"
            ? pathname.startsWith("/scan")
            : item.label === "Projeksiyon"
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
                      ? pathname === "/"
                      : false;
          return <a aria-current={active ? "page" : undefined} className={active ? "active" : ""} href={item.href} key={`${item.label}-${index}`}>
            <i aria-hidden="true">{item.icon}</i><span>{item.label}</span>
          </a>;
        })}
        {pathname.startsWith("/stocks/") ? <a aria-current="page" className="active contextual-nav-item" href={pathname}>
          <i aria-hidden="true">◎</i><span>Detaylı Analiz</span><em>BAĞLAM</em>
        </a> : null}
      </nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-status">
        <div className="system-line" aria-live="polite">{systemState === "ready" ? <span className="live-dot" /> : <span aria-hidden="true">○</span>}<strong>{statusCopy.system}</strong></div>
        <span className="sidebar-meta">FastAPI · Next.js · güvenli oturum</span>
        <span className="sidebar-user">{user?.email ?? "Oturum bekleniyor"}</span>
      </div>
    </aside>
    <div className="app-content" id="main-content" role="main" tabIndex={-1}>
      <header className="topbar">
        <div className="topbar-title"><span>IZFIN</span><b>{pageLabel}</b></div>
        <div className="topbar-actions">
          <span className="api-chip" aria-live="polite">{systemState === "ready" ? <i className="live-dot" /> : null}{statusCopy.api}</span>
        </div>
      </header>
      <UsageGuide />
      {children}
    </div>
  </div>;
}
