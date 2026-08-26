# IZFIN Streamlit → Web parity audit

_Date: 2026-08-26 · scope: current `develop`_

## Rule used for this audit

The web client must call the existing FastAPI and Firebase contracts. It must not create a second scoring, signal, projection, performance, or watchlist engine.

## Confirmed parity

| Legacy capability | Web surface | Source of calculation/state |
| --- | --- | --- |
| Personal watchlist and scan universe | `/scan` | existing watchlist repository plus `scan/universe` |
| BIST 30, BIST 100, ABD technology profiles | `/scan` | `izfin_core.market_universe` through `/scan/profiles` |
| Smart-scan job, progress, history, filters, KPI and detail handoff | `/scan` | existing scan runner and job store |
| Stock detail and 45-day scenario | stock detail / projection | job-scoped technical panel and existing projection service |
| Performance positions and scorecard | `/performance` | existing signal/performance repositories and presenters |
| Daily Core strategy backtest | `/strategy-lab` | existing backtest service |
| Legal documents, consent, export, deletion | `/account` | existing account/legal services |

## Confirmed gaps before this audit

1. The web had only inline email/password sign-in; Streamlit also had registration, password reset, email verification, Google sign-in, consent, and a post-registration personal baseline.
2. The performance empty state still linked to the old Streamlit scan anchor instead of the dedicated web scan route.
3. A visually populated screen is not evidence of a live protected workflow. Signed-in browser acceptance against the current Cloud Run API remains a release gate.

## Current remediation order

1. Dedicated identity routes: existing Firebase sign-in/sign-up/reset/verification/Google lifecycle plus the existing IZFIN profile and default-watchlist bootstrap.
2. First-run onboarding that uses the same personal-list and scan APIs.
3. Cross-screen signed-in desktop/mobile acceptance. Any missing Streamlit action found there is added as an API-backed port, never as a new scoring rule.

