from __future__ import annotations

import re
import time

import cp6_browser_acceptance as cp6


def create_qa_account_fixed(browser):
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
    captcha_text = captcha_label.inner_text()
    numbers = [int(value) for value in re.findall(r"\d+", captcha_text)]
    if len(numbers) < 2:
        raise AssertionError(f"captcha operands not found: {captcha_text!r}")
    captcha_label.locator("input").fill(str(numbers[0] + numbers[1]))

    checks = form.locator('label.auth-checkbox input[type="checkbox"]')
    checks.nth(0).check()
    checks.nth(1).check()
    form.locator('button[type="submit"]').click()
    page.wait_for_url(re.compile(r"/scan"), timeout=45_000)
    cp6.wait_render(page)

    changed = cp6.mark_persisted_user_verified(page)
    cp6.log(f"marked {changed} persisted Firebase user record(s) emailVerified=true")
    page.reload(wait_until="domcontentloaded", timeout=45_000)
    cp6.wait_render(page)
    try:
        page.locator(".app-shell").wait_for(state="visible", timeout=15_000)
    except Exception as exc:
        gate_text = page.locator("body").inner_text()[:1500]
        raise AssertionError(f"authenticated workspace did not open after QA verification shim. Body: {gate_text}") from exc
    return context, page, email


cp6.create_qa_account = create_qa_account_fixed
cp6.main()
