from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Route, sync_playwright

BASE_URL = os.environ.get(
    "IZFIN_SCAN_QA_BASE_URL",
    "https://izfin-web-git-fix-scan-selection-continuity-adopcin-7216.vercel.app",
).rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("IZFIN_SCAN_QA_ARTIFACT_DIR", "scan-selection-browser-artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    print(f"[SCAN-SELECTION-QA] {message}", flush=True)


def wait_render(page: Page, delay_ms: int = 900) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(delay_ms)


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(ARTIFACT_DIR / f"{name}.png"), full_page=True)


def install_identitytoolkit_routes(context: BrowserContext) -> None:
    def handler(route: Route) -> None:
        url = route.request.url
        if "accounts:sendOobCode" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"email": "scan.qa@example.com"}))
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
    email = f"izfin.scan.qa.{int(time.time())}@example.com"
    password = "IzfinQa2026A1"

    page.goto(f"{BASE_URL}/auth?next=%2Fscan", wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    page.get_by_role("button", name="Kayıt Ol", exact=True).click()

    form = page.locator("form.auth-screen-form")
    form.locator('input[type="email"]').fill(email)
    passwords = form.locator('input[type="password"]')
    passwords.nth(0).fill(password)
    passwords.nth(1).fill(password)

    captcha_label = form.locator("label").filter(has_text="İnsan doğrulaması").first
    numbers = [int(value) for value in re.findall(r"\d+", captcha_label.inner_text())]
    if len(numbers) < 2:
        raise AssertionError("captcha operands not found")
    captcha_label.locator("input").fill(str(numbers[0] + numbers[1]))

    checks = form.locator('label.auth-checkbox input[type="checkbox"]')
    checks.nth(0).check()
    checks.nth(1).check()
    form.locator('button[type="submit"]').click()
    page.wait_for_url(re.compile(r"/scan"), timeout=45_000)
    wait_render(page)

    changed = mark_persisted_user_verified(page)
    log(f"marked {changed} persisted Firebase user record(s) emailVerified=true")
    page.reload(wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    page.locator(".app-shell").wait_for(state="visible", timeout=20_000)
    return context, page, email


def stored_selection(page: Page) -> str:
    return page.evaluate(
        """() => {
          for (let i = 0; i < localStorage.length; i += 1) {
            const key = localStorage.key(i) || '';
            if (!key.startsWith('izfin:analysis-context:')) continue;
            try {
              const parsed = JSON.parse(localStorage.getItem(key) || '{}');
              if (parsed.selectedTicker) return String(parsed.selectedTicker);
            } catch {}
          }
          return '';
        }"""
    )


def assert_selected(page: Page, ticker: str, phase: str) -> None:
    selector = page.locator("#scan-decision-ticker")
    selector.wait_for(state="visible", timeout=30_000)
    value = selector.input_value()
    heading = page.locator(".scan-decision-identity h3").inner_text()
    persisted = stored_selection(page)
    if value != ticker or heading != ticker or persisted != ticker:
        raise AssertionError(
            f"{phase}: selection mismatch value={value!r} heading={heading!r} persisted={persisted!r} expected={ticker!r}"
        )


def launch_scan(page: Page) -> None:
    page.goto(f"{BASE_URL}/scan", wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    page.locator(".app-shell").wait_for(state="visible", timeout=20_000)

    profile = page.locator(".scan-profile-label select")
    profile.wait_for(state="visible", timeout=20_000)
    options = profile.locator("option").all_text_contents()
    preferred = "ABD Büyük Teknoloji" if "ABD Büyük Teknoloji" in options else ("BIST 30" if "BIST 30" in options else "Kendi Listem")
    profile.select_option(label=preferred)
    page.wait_for_timeout(1200)
    log(f"using scan profile: {preferred}")

    launch = page.locator("button.scan-launch").first
    launch.wait_for(state="visible", timeout=20_000)
    launch.click()
    dialog = page.locator("dialog.scan-lock-overlay[open]")
    dialog.wait_for(state="visible", timeout=20_000)
    try:
        dialog.wait_for(state="hidden", timeout=180_000)
    except Exception as exc:
        shot(page, "scan-timeout")
        raise AssertionError("live scan did not finish within 180 seconds") from exc

    page.locator(".scan-result-symbol").first.wait_for(state="visible", timeout=30_000)
    count = page.locator(".scan-result-symbol").count()
    if count < 2:
        shot(page, "scan-too-few-results")
        raise AssertionError(f"need at least two scan results for continuity acceptance, got {count}")
    shot(page, "scan-complete")


def choose_non_first_projectable_result(page: Page) -> tuple[str, str]:
    symbols = page.locator(".scan-result-symbol").all_text_contents()
    initial = page.locator("#scan-decision-ticker").input_value() if page.locator("#scan-decision-ticker").count() else ""

    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol or symbol == initial:
            continue
        page.get_by_role("button", name=symbol, exact=True).first.click()
        page.wait_for_timeout(1200)
        card = page.locator(".scan-decision-card")
        if not card.count() or not card.is_visible():
            continue
        links = card.locator(".scan-decision-actions a")
        if links.count() < 2:
            continue
        assert_selected(page, symbol, "after table selection")
        return initial, symbol

    shot(page, "no-secondary-projectable-result")
    raise AssertionError(f"no non-initial result with detail/projection actions; symbols={symbols!r}, initial={initial!r}")


def test_continuity(page: Page) -> dict:
    launch_scan(page)
    initial, selected = choose_non_first_projectable_result(page)
    log(f"selected non-first result: initial={initial} selected={selected}")
    shot(page, "selected-secondary-result")

    page.reload(wait_until="domcontentloaded", timeout=45_000)
    wait_render(page, 1400)
    assert_selected(page, selected, "scan refresh")

    detail_link = page.locator(".scan-decision-actions a").filter(has_text="Detaylı analizi aç").first
    detail_href = detail_link.get_attribute("href") or ""
    detail_link.click()
    page.wait_for_url(re.compile(r"/stocks/"), timeout=45_000)
    page.locator(".detail-page h1").wait_for(state="visible", timeout=30_000)
    detail_heading = page.locator(".detail-page h1").inner_text().strip().upper()
    if detail_heading != selected or "job_id=" not in page.url:
        raise AssertionError(f"detail context mismatch heading={detail_heading!r} url={page.url!r} selected={selected!r}")
    shot(page, "detail-selected-result")

    projection_link = page.locator("a.projection-cta")
    projection_link.wait_for(state="visible", timeout=30_000)
    projection_link.click()
    page.wait_for_url(re.compile(r"/projection"), timeout=45_000)
    page.locator(".projection-page").wait_for(state="visible", timeout=30_000)
    page.wait_for_timeout(1800)
    body = page.locator(".projection-page").inner_text().upper()
    if selected not in body or "job_id=" not in page.url or "ticker=" not in page.url:
        raise AssertionError(f"projection context mismatch url={page.url!r} selected={selected!r}")
    shot(page, "projection-selected-result")

    page.goto(f"{BASE_URL}/scan#scan-result", wait_until="domcontentloaded", timeout=45_000)
    wait_render(page, 1600)
    assert_selected(page, selected, "return to scan")

    page.reload(wait_until="domcontentloaded", timeout=45_000)
    wait_render(page, 1600)
    assert_selected(page, selected, "final scan refresh")
    shot(page, "scan-final-selection")

    return {
        "initial_ticker": initial,
        "selected_ticker": selected,
        "detail_href": detail_href,
        "final_url": page.url,
        "stored_selection": stored_selection(page),
    }


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
        context = None
        page = None
        try:
            context, page, email = create_qa_account(browser)
            summary["qa_email"] = email
            try:
                summary["continuity"] = test_continuity(page)
            finally:
                summary["cleanup"] = delete_qa_account(page)
        finally:
            if context is not None:
                context.close()
            browser.close()

    summary_path = ARTIFACT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"PASS — summary written to {summary_path}")


if __name__ == "__main__":
    main()
