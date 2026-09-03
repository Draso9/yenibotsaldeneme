from __future__ import annotations

import json
import re
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Route, sync_playwright

BASE_URL = "https://izfin-web.vercel.app"
ARTIFACT_DIR = Path("cp6-production-focus-artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    print(f"[CP6-PROD] {message}", flush=True)


def wait_render(page: Page, milliseconds: int = 900) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(milliseconds)


def install_verification_shim(context: BrowserContext) -> None:
    def handler(route: Route) -> None:
        url = route.request.url
        if "accounts:sendOobCode" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"email": "qa@example.com"}))
            return
        if "accounts:lookup" in url:
            response = route.fetch()
            data = response.json()
            if isinstance(data, dict):
                for user in data.get("users", []):
                    if isinstance(user, dict):
                        user["emailVerified"] = True
            route.fulfill(response=response, body=json.dumps(data))
            return
        route.continue_()

    context.route("**/identitytoolkit.googleapis.com/**", handler)


def create_qa_account(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    install_verification_shim(context)
    page = context.new_page()
    email = f"izfin.cp6.prod.{int(time.time())}@example.com"
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
        raise AssertionError(f"captcha operands not found: {captcha_label.inner_text()!r}")
    captcha_label.locator("input").fill(str(numbers[0] + numbers[1]))
    checks = form.locator('label.auth-checkbox input[type="checkbox"]')
    checks.nth(0).check()
    checks.nth(1).check()
    form.locator('button[type="submit"]').click()
    page.wait_for_url(re.compile(r"/scan"), timeout=45_000)
    wait_render(page)
    page.reload(wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    page.locator(".app-shell").wait_for(state="visible", timeout=20_000)
    log(f"QA account opened authenticated workspace: {email}")
    return context, page, email


def run_modal_focus_verification(page: Page) -> dict:
    page.goto(f"{BASE_URL}/scan", wait_until="domcontentloaded", timeout=45_000)
    wait_render(page)
    page.locator(".app-shell").wait_for(state="visible", timeout=20_000)

    form = page.locator("form.scan-watchlist-form")
    form.wait_for(state="visible", timeout=20_000)
    form.locator("input").fill("AAPL")
    form.locator('button[type="submit"]').click()
    page.locator(".ticker-list").filter(has_text="AAPL").wait_for(state="visible", timeout=20_000)

    launch = page.locator("button.scan-launch").first
    page.wait_for_function(
        "() => { const el = document.querySelector('button.scan-launch'); return !!el && !el.disabled; }",
        timeout=20_000,
    )
    launch.focus()
    page.keyboard.press("Enter")

    dialog = page.locator("dialog.scan-lock-overlay[open]")
    dialog.wait_for(state="visible", timeout=20_000)
    modal_state = page.evaluate(
        """() => {
          const d = document.querySelector('dialog.scan-lock-overlay[open]');
          return {
            isModal: Boolean(d && d.matches(':modal')),
            focusInside: Boolean(d && d.contains(document.activeElement)),
            activeTag: document.activeElement?.tagName || '',
            activeText: document.activeElement?.innerText || '',
          };
        }"""
    )
    if not modal_state["isModal"] or not modal_state["focusInside"]:
        raise AssertionError(f"modal did not own focus: {modal_state}")

    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    if not dialog.is_visible():
        raise AssertionError("progress modal dismissed on Escape while scan was still running")

    page.locator("dialog.scan-lock-overlay[open]").wait_for(state="hidden", timeout=120_000)
    page.wait_for_timeout(250)
    focus_after = page.evaluate(
        """() => ({
          inMain: Boolean(document.getElementById('main-content')?.contains(document.activeElement)),
          tag: document.activeElement?.tagName || '',
          id: document.activeElement?.id || '',
          className: String(document.activeElement?.className || ''),
          text: document.activeElement?.innerText || document.activeElement?.getAttribute?.('aria-label') || '',
        })"""
    )
    if not focus_after["inMain"]:
        raise AssertionError(f"focus did not return to main content after modal close: {focus_after}")

    page.screenshot(path=str(ARTIFACT_DIR / "scan-after-modal-production.png"), full_page=True)
    return {"modal": modal_state, "focus_after": focus_after}


def delete_qa_account(page: Page, email: str) -> str:
    try:
        page.goto(f"{BASE_URL}/account", wait_until="domcontentloaded", timeout=45_000)
        wait_render(page)
        page.locator(".app-shell").wait_for(state="visible", timeout=20_000)
        page.get_by_role("button", name="Hesabı Sil", exact=True).click()
        delete_form = page.locator(".account-delete-form")
        delete_form.wait_for(state="visible", timeout=10_000)
        email_input = delete_form.locator("label").filter(has_text="E-posta adresin").locator("input")
        email_input.fill(email)
        phrase = delete_form.locator("label").filter(has_text="Onay ifadesi").locator("input")
        phrase.fill("HESABIMI KALICI OLARAK SİL")
        delete_form.locator('.account-check input[type="checkbox"]').check()
        delete_form.get_by_role("button", name="Hesabımı kalıcı olarak sil", exact=True).click()
        page.wait_for_url(re.compile(r"/auth"), timeout=30_000)
        return "deleted"
    except Exception as exc:
        log(f"QA cleanup failed: {exc}")
        return "cleanup-failed"


def main() -> None:
    summary: dict[str, object] = {"base_url": BASE_URL}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = None
        page = None
        email = ""
        try:
            context, page, email = create_qa_account(browser)
            log("starting production scan modal focus verification")
            summary["scan_modal"] = run_modal_focus_verification(page)
            log(f"PASS focus_after={summary['scan_modal']['focus_after']}")
        finally:
            if page is not None and email:
                summary["cleanup"] = delete_qa_account(page, email)
            if context is not None:
                context.close()
            browser.close()

    output = ARTIFACT_DIR / "summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"summary written to {output}")


if __name__ == "__main__":
    main()
