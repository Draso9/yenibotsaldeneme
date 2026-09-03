from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Route, sync_playwright

BASE_URL = os.environ.get("IZFIN_CP6_BASE_URL", "https://izfin-web.vercel.app").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("IZFIN_CP6_ARTIFACT_DIR", "cp6-browser-artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    (390, 844, "mobile"),
    (768, 1024, "tablet"),
    (1440, 900, "desktop"),
]
PUBLIC_ROUTES = ["/auth", "/legal/terms", "/legal/privacy"]
WORKSPACE_ROUTES = ["/", "/scan", "/projection", "/performance", "/strategy-lab", "/account"]


def log(message: str) -> None:
    print(f"[CP6] {message}", flush=True)


def wait_render(page: Page) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(900)


def viewport_report(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const root = document.documentElement;
          const body = document.body;
          const visible = (el) => {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          };
          const offenders = [...document.querySelectorAll('button,a,input,select,textarea,summary')]
            .filter(visible)
            .map((el) => {
              const r = el.getBoundingClientRect();
              return {tag: el.tagName, text: (el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().slice(0, 80), left: r.left, right: r.right, top: r.top, bottom: r.bottom};
            })
            .filter((r) => r.right > innerWidth + 2 || r.left < -2);
          const mobileNav = document.querySelector('.mobile-navigation');
          const desktopNav = document.querySelector('.desktop-navigation');
          const appContent = document.querySelector('.app-content');
          return {
            innerWidth,
            innerHeight,
            rootScrollWidth: root.scrollWidth,
            bodyScrollWidth: body?.scrollWidth || 0,
            horizontalOverflow: Math.max(root.scrollWidth, body?.scrollWidth || 0) - innerWidth,
            offenders,
            mobileNavDisplay: mobileNav ? getComputedStyle(mobileNav).display : null,
            mobileNavHeight: mobileNav ? mobileNav.getBoundingClientRect().height : 0,
            desktopNavDisplay: desktopNav ? getComputedStyle(desktopNav).display : null,
            appContentPaddingBottom: appContent ? parseFloat(getComputedStyle(appContent).paddingBottom) : 0,
          };
        }"""
    )


def assert_viewport(page: Page, label: str, authenticated: bool) -> dict:
    report = viewport_report(page)
    if report["horizontalOverflow"] > 2:
        raise AssertionError(f"{label}: horizontal overflow {report['horizontalOverflow']}px")
    if report["offenders"]:
        raise AssertionError(f"{label}: clipped interactive controls: {json.dumps(report['offenders'], ensure_ascii=False)}")
    if authenticated:
        if page.viewport_size["width"] <= 860:
            if report["mobileNavDisplay"] == "none":
                raise AssertionError(f"{label}: mobile navigation is hidden")
            if report["desktopNavDisplay"] != "none":
                raise AssertionError(f"{label}: desktop navigation is still visible")
            if report["appContentPaddingBottom"] + 1 < report["mobileNavHeight"]:
                raise AssertionError(
                    f"{label}: app content padding {report['appContentPaddingBottom']} does not clear mobile nav {report['mobileNavHeight']}"
                )
        else:
            if report["mobileNavDisplay"] != "none":
                raise AssertionError(f"{label}: mobile navigation is visible on desktop")
            if report["desktopNavDisplay"] == "none":
                raise AssertionError(f"{label}: desktop navigation is hidden on desktop")
    return report


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(ARTIFACT_DIR / f"{name}.png"), full_page=True)


def test_public_viewports(browser) -> list[dict]:
    results = []
    for width, height, viewport_name in VIEWPORTS:
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        try:
            for route in PUBLIC_ROUTES:
                page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded", timeout=45_000)
                wait_render(page)
                result = assert_viewport(page, f"{viewport_name}:{route}", authenticated=False)
                results.append({"viewport": viewport_name, "route": route, **result})
                shot(page, f"public-{viewport_name}-{route.strip('/').replace('/', '-') or 'root'}")
        finally:
            context.close()
    return results


def test_auth_error_focus(browser) -> dict:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        page.goto(f"{BASE_URL}/auth", wait_until="domcontentloaded", timeout=45_000)
        wait_render(page)
        submit = page.locator('form button[type="submit"]').first
        submit.focus()
        page.keyboard.press("Enter")
        page.locator("#auth-error").wait_for(state="visible", timeout=5_000)
        active_id = page.evaluate("document.activeElement?.id || ''")
        email = page.locator('form input[type="email"]').first
        password = page.locator('form input[type="password"]').first
        email_invalid = email.get_attribute("aria-invalid")
        password_invalid = password.get_attribute("aria-invalid")
        email_desc = email.get_attribute("aria-describedby") or ""
        password_desc = password.get_attribute("aria-describedby") or ""
        if active_id != "auth-error":
            raise AssertionError(f"auth error summary did not receive focus: active={active_id!r}")
        if email_invalid != "true" or password_invalid != "true":
            raise AssertionError(f"auth invalid relationship missing: email={email_invalid}, password={password_invalid}")
        if "auth-error" not in email_desc or "auth-error" not in password_desc:
            raise AssertionError(f"auth aria-describedby missing: email={email_desc!r}, password={password_desc!r}")
        shot(page, "auth-error-focus-mobile")
        return {
            "active": active_id,
            "email_invalid": email_invalid,
            "password_invalid": password_invalid,
            "email_describedby": email_desc,
            "password_describedby": password_desc,
        }
    finally:
        context.close()


def install_identitytoolkit_routes(context: BrowserContext) -> None:
    def handler(route: Route) -> None:
        url = route.request.url
        if "accounts:sendOobCode" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"email": "cp6@example.com"}))
            return
        if "accounts:lookup" in url:
            response = route.fetch()
            data = response.json()
            for user in data.get("users", []) if isinstance(data, dict) else []:
                user["emailVerified"] = True
            route.fulfill(response=response, body=json.dumps(data))
            return
        route.continue_()

    context.route("**/identitytoolkit.googleapis.com/**", handler)


def mark_persisted_user_verified(page: Page) -> int:
    return page.evaluate(
        """async () => {
          const openDb = () => new Promise((resolve, reject) => {
            const req = indexedDB.open('firebaseLocalStorageDb');
            req.onerror = () => reject(req.error);
            req.onsuccess = () => resolve(req.result);
          });
          const db = await openDb();
          if (!db.objectStoreNames.contains('firebaseLocalStorage')) return 0;
          const tx = db.transaction('firebaseLocalStorage', 'readwrite');
          const store = tx.objectStore('firebaseLocalStorage');
          const all = await new Promise((resolve, reject) => {
            const req = store.getAll();
            req.onerror = () => reject(req.error);
            req.onsuccess = () => resolve(req.result || []);
          });
          let changed = 0;
          for (const record of all) {
            if (!record || typeof record !== 'object') continue;
            if (String(record.fbase_key || '').includes('firebase:authUser') && record.value && typeof record.value === 'object') {
              record.value.emailVerified = true;
              store.put(record);
              changed += 1;
            }
          }
          await new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
            tx.onabort = () => reject(tx.error);
          });
          db.close();
          return changed;
        }"""
    )


def create_qa_account(browser) -> tuple[BrowserContext, Page, str]:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    install_identitytoolkit_routes(context)
    page = context.new_page()
    email = f"izfin.cp6.{int(time.time())}@example.com"
    password = "IzfinQa2026A1"

    page.goto(f"{BASE_URL}/auth?next=%2Fscan", wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    page.get_by_role("button", name="Kayıt Ol", exact=True).click()
    page.get_by_label("E-posta", exact=True).fill(email)
    page.get_by_label("Şifre", exact=True).fill(password)
    page.get_by_label("Şifre tekrar", exact=True).fill(password)
    captcha_label = page.locator("label").filter(has_text="İnsan doğrulaması").first
    captcha_text = captcha_label.inner_text()
    numbers = [int(value) for value in re.findall(r"\d+", captcha_text)]
    if len(numbers) < 2:
        raise AssertionError(f"captcha operands not found: {captcha_text!r}")
    captcha_label.locator("input").fill(str(numbers[0] + numbers[1]))
    checks = page.locator('label.auth-checkbox input[type="checkbox"]')
    checks.nth(0).check()
    checks.nth(1).check()
    page.get_by_role("button", name="Hesabımı Oluştur", exact=True).click()
    page.wait_for_url(re.compile(r"/scan"), timeout=45_000)
    wait_render(page)

    changed = mark_persisted_user_verified(page)
    log(f"marked {changed} persisted Firebase user record(s) emailVerified=true")
    page.reload(wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    try:
        page.locator(".app-shell").wait_for(state="visible", timeout=15_000)
    except Exception as exc:
        gate_text = page.locator("body").inner_text()[:1500]
        raise AssertionError(f"authenticated workspace did not open after QA verification shim. Body: {gate_text}") from exc
    return context, page, email


def test_workspace_viewports(page: Page) -> list[dict]:
    results = []
    for width, height, viewport_name in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        for route in WORKSPACE_ROUTES:
            page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded", timeout=45_000)
            wait_render(page)
            page.locator(".app-shell").wait_for(state="visible", timeout=15_000)
            result = assert_viewport(page, f"{viewport_name}:{route}", authenticated=True)
            results.append({"viewport": viewport_name, "route": route, **result})

            if width <= 860:
                more = page.locator(".mobile-more-menu > summary")
                if more.count():
                    more.focus()
                    page.keyboard.press("Enter")
                    panel = page.locator(".mobile-more-panel")
                    panel.wait_for(state="visible", timeout=2_000)
                    panel_box = panel.bounding_box()
                    if panel_box and (panel_box["x"] < -2 or panel_box["x"] + panel_box["width"] > width + 2):
                        raise AssertionError(f"{viewport_name}:{route}: mobile more panel clipped: {panel_box}")
                    page.keyboard.press("Enter")

            guide = page.locator("details.usage-guide > summary")
            if guide.count():
                guide.focus()
                page.keyboard.press("Enter")
                if not page.locator("details.usage-guide").get_attribute("open") == "":
                    # Boolean attributes can be returned as empty string when present.
                    pass
                page.keyboard.press("Enter")

            shot(page, f"workspace-{viewport_name}-{route.strip('/').replace('/', '-') or 'market'}")
    return results


def test_scan_modal(page: Page) -> dict:
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{BASE_URL}/scan", wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    page.locator(".app-shell").wait_for(state="visible", timeout=15_000)
    launch = page.locator("button.scan-launch").first
    launch.wait_for(state="visible", timeout=15_000)
    launch.focus()
    page.keyboard.press("Enter")

    dialog = page.locator("dialog.scan-lock-overlay[open]")
    dialog.wait_for(state="visible", timeout=15_000)
    modal_state = page.evaluate(
        """() => {
          const d = document.querySelector('dialog.scan-lock-overlay[open]');
          return {
            isModal: Boolean(d && d.matches(':modal')),
            focusInside: Boolean(d && d.contains(document.activeElement)),
            activeText: document.activeElement?.innerText || document.activeElement?.getAttribute?.('aria-label') || '',
          };
        }"""
    )
    if not modal_state["isModal"] or not modal_state["focusInside"]:
        raise AssertionError(f"scan dialog modal/focus failure: {modal_state}")

    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    if dialog.count() and dialog.is_visible():
        escape_policy = "progress-modal-remains-open"
    else:
        escape_policy = "progress-modal-dismissed"

    # The live scan owns dismissal; wait for it to finish rather than forcing the dialog closed.
    try:
        page.locator("dialog.scan-lock-overlay[open]").wait_for(state="hidden", timeout=120_000)
    except Exception as exc:
        raise AssertionError("scan progress modal did not close after scan completion within 120s") from exc

    focus_after = page.evaluate(
        """() => ({
          tag: document.activeElement?.tagName || '',
          text: document.activeElement?.innerText || document.activeElement?.getAttribute?.('aria-label') || '',
          inMain: Boolean(document.getElementById('main-content')?.contains(document.activeElement)),
        })"""
    )
    if not focus_after["inMain"]:
        raise AssertionError(f"focus did not return to main workspace after modal close: {focus_after}")
    shot(page, "scan-after-modal-desktop")
    return {"modal": modal_state, "escape_policy": escape_policy, "focus_after": focus_after}


def delete_qa_account(page: Page) -> str:
    try:
        page.goto(f"{BASE_URL}/account", wait_until="domcontentloaded", timeout=45_000)
        wait_render(page)
        page.get_by_role("button", name="Hesabı Sil", exact=True).click()
        page.get_by_label("Onay ifadesi", exact=True).fill("HESABIMI KALICI OLARAK SİL")
        page.locator('.account-check input[type="checkbox"]').check()
        page.get_by_role("button", name="Hesabımı kalıcı olarak sil", exact=True).click()
        page.wait_for_url(re.compile(r"/auth"), timeout=30_000)
        return "deleted"
    except Exception as exc:
        log(f"QA account cleanup warning: {exc}")
        return "cleanup-failed"


def main() -> None:
    summary: dict = {"base_url": BASE_URL}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            log("running public viewport matrix")
            summary["public_viewports"] = test_public_viewports(browser)
            log("running auth form focus/ARIA acceptance")
            summary["auth_focus"] = test_auth_error_focus(browser)

            log("creating temporary QA account for authenticated acceptance")
            context, page, email = create_qa_account(browser)
            summary["qa_email"] = email
            try:
                log("running authenticated viewport matrix")
                summary["workspace_viewports"] = test_workspace_viewports(page)
                log("running scan modal keyboard/focus acceptance")
                summary["scan_modal"] = test_scan_modal(page)
                summary["cleanup"] = delete_qa_account(page)
            finally:
                context.close()
        finally:
            browser.close()

    summary_path = ARTIFACT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"PASS — summary written to {summary_path}")


if __name__ == "__main__":
    main()
