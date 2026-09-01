type MobileNavigationProps = {
  pathname: string;
  isAdmin: boolean;
};

const primaryItems = [
  { icon: "⌂", label: "Piyasa", href: "/" },
  { icon: "⌕", label: "Tarama", href: "/scan" },
  { icon: "◈", label: "Projeksiyon", href: "/projection" },
  { icon: "◫", label: "Performans", href: "/performance" },
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

export function MobileNavigation({ pathname, isAdmin }: MobileNavigationProps) {
  const moreActive = pathname.startsWith("/strategy-lab")
    || pathname.startsWith("/account")
    || pathname.startsWith("/admin/quality");

  return (
    <nav aria-label="Mobil navigasyon" className="mobile-navigation">
      {primaryItems.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <a
            aria-current={active ? "page" : undefined}
            className={active ? "active" : ""}
            data-mobile-primary="true"
            href={item.href}
            key={item.href}
          >
            <i aria-hidden="true">{item.icon}</i>
            <span>{item.label}</span>
          </a>
        );
      })}
      <details className={`mobile-more-menu${moreActive ? " active" : ""}`} data-mobile-primary="true">
        <summary aria-label="Diğer sayfaları aç">
          <i aria-hidden="true">•••</i>
          <span>Diğer</span>
        </summary>
        <div className="mobile-more-panel">
          <a aria-current={pathname.startsWith("/strategy-lab") ? "page" : undefined} href="/strategy-lab">Strateji Lab</a>
          <a aria-current={pathname.startsWith("/account") ? "page" : undefined} href="/account">Hesap</a>
          {isAdmin ? <a aria-current={pathname.startsWith("/admin/quality") ? "page" : undefined} href="/admin/quality">Admin QA</a> : null}
        </div>
      </details>
    </nav>
  );
}
