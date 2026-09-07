# Smart Scan selection continuity — 2026-09-07

Base: develop 3cd7d1bea2dbed8bebca3973e28cd671d89abb34.
Branch: fix/scan-selection-continuity. Main untouched.

## Reproduced defect and scoped fix

With result rows AAA/BBB, remembered BBB and only AAA available in
projectable_tickers, publishCompletedScan overwrote BBB with AAA during recovery.
The baseline fails the regression with actual AAA versus expected BBB.

Remove the projection-based selection writer. Existing ScanResult owns selection
validation against actual result rows, preserving a valid ticker and otherwise
selecting the first row. This matches Streamlit detay_secimi_hazirla.
No backend, auth, provider, visual layout or financial calculation changes.
The resultTickers helper remains unchanged for projection consumers.

The backend detail service requires a technical panel: a missing panel produces
404. The regression fixture models that response and verifies BBB remains selected
in storage and the table, with the existing detail error rather than AAA's card.
This fixes selection parity, not missing technical data generation.

## Automated verification

- Five real React/provider/workspace DOM tests: refresh and route remount; partial
  projection data; table selection/filter/sort/return; stale selection fallback;
  single actual result without projection data.
- Full web suite: 33 passed.
- Full Python suite: 639 passed.
- Typecheck and production build passed.
- Lint: 0 errors, existing 25 warnings.
- Independent review found the initial missing-panel fixture mismatch; corrected
  it and reverified baseline RED / fixed GREEN. No production defect identified.
- Original product-fix head `73195393e9926dfc7aaa4a16131375a1149f3039`
  passed exact-head IZFIN CI run `34092869090`.
- New scan streaming/polling completion is not separately exercised by the new DOM
  tests; existing recovery tests remain green and all completion callers use the
  same selection-neutral publisher.

## Authenticated real Chromium acceptance

A one-off Playwright/Chromium acceptance harness was used only to close the live
selection-continuity gate. The first run `34096145987` was RED before IZFIN auth
because the Vercel branch preview was protected; it never reached product flow and
therefore was classified as an environment/harness failure, not a product failure.
No Vercel bypass token was committed.

The acceptance was rerun as GitHub Actions run `34096750329` on exact branch head
`75ee75cbb9f4a256cde842beb0ade4676af4e0bf`, building the PR's Next.js application
locally in production mode while using the normal live Firebase authentication and
Cloud Run API path. The real Chromium job passed.

Observed flow:

- Quick profile: `ABD Büyük Teknoloji`.
- Initial result: `AAPL`; deliberately selected non-first result: `AMZN`.
- `AMZN` remained selected after scan-page refresh.
- Detail navigation opened `/stocks/AMZN?job_id=e282b043-c785-447c-9088-2fd12e9854a2`.
- Projection navigation retained the same ticker/job context.
- Returning to `/scan#scan-result` and refreshing again retained `AMZN` in the UI
  and persisted analysis context.
- Browser acceptance artifact contained five screenshots plus `summary.json`.
- Temporary QA account cleanup completed with `cleanup=deleted`.

The one-off workflow and browser harness were removed immediately after evidence
capture (`a68a25eaed30da26b9134342a3a2f0168e21b8ab` and
`98fcb6c42bb2e38fefa81e538d8485b51f94165d`). They are not intended to remain in
the merged product branch.

## Handoff

PR #147 remains an open draft against `develop`; no merge has been performed.
Run the ordinary IZFIN Python/Web quality gates on the final cleanup/documentation
head, review the final diff boundary, then the package can be considered merge-ready
if those gates remain green. `main` stays untouched. Do not reopen the merged
legal/detail-context packages.
