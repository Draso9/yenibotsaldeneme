from __future__ import annotations

import json
import re
import time

import cp6_browser_acceptance as cp6


def create_qa_account(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    cp6.install_identitytoolkit_routes(context)
    page = context.new_page()
    email = f"izfin.cp6.{int(time.time())}@example.com"
    password = "IzfinQa2026A1"

    page.goto(f"{cp6.BASE_URL}/auth?next=%2Fscan", wait_until="domcontentloaded", timeout=45_000)
    cp6.wait_render(page)
    page.get_by_role("button", name="Kayıt Ol", exact=True).click()
    form = page.locator("form.auth-screen-form")
    form.locator('input[type="email"]').fill(email)
    passwords = form.locator('input[type="password"]')
    passwords.nth(0).fill(password)
    passwords.nth(1).fill(password)
    captcha_label = form.locator("label").filter(has_text="İnsan doğrulaması").first
    numbers = [int(value) for value in re.findall(r"\d+", captcha_label.inner_text())]
    captcha_label.locator("input").fill(str(numbers[0] + numbers[1]))
    checks = form.locator('label.auth-checkbox input[type="checkbox"]')
    checks.nth(0).check()
    checks.nth(1).check()
    form.locator('button[type="submit"]').click()
    page.wait_for_url(re.compile(r"/scan"), timeout=45_000)
    cp6.wait_render(page)
    page.reload(wait_until="domcontentloaded", timeout=45_000)
    cp6.wait_render(page)
    page.locator(".app-shell").wait_for(state="visible", timeout=15_000)
    return context, page


def assert_shell(page, route):
    try:
        page.locator(".app-shell").wait_for(state="visible", timeout=15_000)
    except Exception as exc:
        body = page.locator("body").inner_text()[:1800]
        raise AssertionError(f"desktop:{route}: app-shell missing at {page.url}. Body: {body}") from exc


def test_remaining_desktop(page):
    results = []
    for route in ["/performance", "/strategy-lab", "/account"]:
        page.goto(f"{cp6.BASE_URL}{route}", wait_until="domcontentloaded", timeout=45_000)
        cp6.wait_render(page)
        assert_shell(page, route)
        result = cp6.assert_viewport(page, f"desktop:{route}", authenticated=True)
        results.append({"route": route, **result})

        guide = page.locator("details.usage-guide > summary")
        if guide.count():
            guide.focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(100)
            if page.locator("details.usage-guide").get_attribute("open") is None:
                raise AssertionError(f"desktop:{route}: usage guide did not open by keyboard")
            page.keyboard.press("Enter")

        if route == "/performance":
            periods = page.locator(".performance-period button")
            periods.nth(0).focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(250)
            if "active" not in (periods.nth(0).get_attribute("class") or ""):
                raise AssertionError("desktop:/performance: 1G period did not activate by keyboard")
            periods.nth(4).focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(250)
            if "active" not in (periods.nth(4).get_attribute("class") or ""):
                raise AssertionError("desktop:/performance: 45G period did not activate by keyboard")

        cp6.shot(page, f"remaining-desktop-{route.strip('/')}")
    return results


def test_scan_modal_one_symbol(page):
    page.goto(f"{cp6.BASE_URL}/scan", wait_until="domcontentloaded", timeout=45_000)
    cp6.wait_render(page)
    assert_shell(page, "/scan-modal")

    form = page.locator("form.scan-watchlist-form")
    form.wait_for(state="visible", timeout=15_000)
    form.locator("input").fill("AAPL")
    form.locator('button[type="submit"]').click()
    page.locator(".ticker-list").filter(has_text="AAPL").wait_for(state="visible", timeout=15_000)

    launch = page.locator("button.scan-launch")
    page.wait_for_function("() => { const el = document.querySelector('button.scan-launch'); return !!el && !el.disabled; }", timeout=20_000)
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
            activeTag: document.activeElement?.tagName || '',
            activeText: document.activeElement?.innerText || '',
          };
        }"""
    )
    if not modal_state["isModal"] or not modal_state["focusInside"]:
        raise AssertionError(f"scan modal/focus acceptance failed: {modal_state}")

    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    if not dialog.is_visible():
        raise AssertionError("scan progress modal dismissed on Escape while scan was still running")

    page.locator("dialog.scan-lock-overlay[open]").wait_for(state="hidden", timeout=120_000)
    focus_after = page.evaluate(
        """() => ({
          inMain: Boolean(document.getElementById('main-content')?.contains(document.activeElement)),
          tag: document.activeElement?.tagName || '',
          className: document.activeElement?.className || '',
        })"""
    )
    if not focus_after["inMain"]:
        raise AssertionError(f"focus did not return to main content after scan modal closed: {focus_after}")
    cp6.shot(page, "remaining-scan-modal-desktop")
    return {"modal": modal_state, "focus_after": focus_after}


def cleanup(page):
    try:
        return cp6.delete_qa_account(page)
    except Exception as exc:
        cp6.log(f"cleanup failed: {exc}")
        return "cleanup-failed"


def main():
    summary = {"base_url": cp6.BASE_URL}
    with cp6.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = None
        page = None
        try:
            cp6.log("creating fresh QA account for remaining desktop acceptance")
            context, page = create_qa_account(browser)
            cp6.log("testing remaining desktop routes")
            summary["remaining_desktop"] = test_remaining_desktop(page)
            cp6.log("testing native scan modal keyboard/focus behavior")
            summary["scan_modal"] = test_scan_modal_one_symbol(page)
        finally:
            if page is not None:
                summary["cleanup"] = cleanup(page)
            if context is not None:
                context.close()
            browser.close()

    path = cp6.ARTIFACT_DIR / "summary-v3.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    cp6.log(f"PASS — remaining acceptance summary written to {path}")


if __name__ == "__main__":
    main()
