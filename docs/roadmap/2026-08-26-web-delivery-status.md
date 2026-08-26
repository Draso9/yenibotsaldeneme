# IZFIN Web Delivery Status

_Last reconciled: 2026-08-26_

## Source of truth

The current implementation status is recorded in GitHub:

1. `develop` is the integrated source of truth.
2. Every implementation package starts from current `develop`, uses a feature branch, and targets `develop` with a pull request.
3. A package is only merged after its GitHub CI is green; the subsequent `develop` CI is also checked.
4. `main` is never a target for this workflow.

This file is intentionally kept in the repository so work can continue from another computer or Codex task without relying on local folders or chat history.

## Completed

- FastAPI foundation and Cloud Run deployment baseline.
- Next.js application foundation: authentication, watchlist, scan, account flow, and web quality CI.
- API/web boundary hardening and responsive web beta groundwork.
- Shared IZFIN web design system and Market Center redesign.
  - Design tokens, shell, mobile navigation, live-strip states, accessible signals, movers panel, and responsive layout are in `develop`.
  - Merged through PR #61 at `fa1fc0aa78ba556bdba3d265e426fed6839ce303`.
  - PR CI was green.

## Current delivery order

The functional screens already exist; the remaining web work is to bring them through the shared design system without changing product behavior.

1. **Akıllı Tarama and stock detail** — shared panels, filtering/result states, detail hierarchy, loading/error/empty states.
2. **Projeksiyon** — consistent scenario cards, assumptions and warning hierarchy.
3. **Performans** — portfolio performance, range controls, readable chart/table states.
4. **Strateji Lab** — strategy configuration, run lifecycle, result/comparison states.
5. **Hesap and legal/OAuth surfaces** — account settings, consent and session states.
6. **Cross-screen quality gate** — mobile/desktop visual regression, accessibility, API contract tests, full CI.
7. **Release preparation** — staging configuration, monitoring, deployment checklist, then optional custom domain/mobile client work.

## Working invariants

- Keep Streamlit running unchanged as the legacy thin shell.
- Reuse FastAPI contracts; do not duplicate business logic in Next.js.
- No fabricated market data: loading, unavailable, and empty states must be explicit.
- Preserve Turkish product language and the established IZFIN visual identity.
- Every completed package is pushed and merged through GitHub before moving on.

## Next package

Start from current `develop`: **Akıllı Tarama and stock-detail design-system migration**.
