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

## Verification

- Five real React/provider/workspace DOM tests: refresh and route remount; partial
  projection data; table selection/filter/sort/return; stale selection fallback;
  single actual result without projection data.
- Full web suite: 33 passed.
- Full Python suite: 639 passed.
- Typecheck and production build passed.
- Lint: 0 errors, existing 25 warnings.
- Independent review found the initial missing-panel fixture mismatch; corrected
  it and reverified baseline RED / fixed GREEN. No production defect identified.
- Browser session inspected: production is at /auth. Authenticated live QA of this
  feature branch is not completed. jsdom tests are not live browser QA.
- New scan streaming/polling completion is not exercised by the new DOM tests;
  existing recovery tests remain green and all completion callers use the same
  selection-neutral publisher.

## Handoff

Open draft PR against develop; wait for exact-head CI before integration advice.
No merge or deploy performed for this package.
Next: authenticated preview QA of non-first selection across scan/detail/projection
and refresh; then address technical-data error UX only if a user-flow gap is
reproduced. Do not reopen the merged legal/detail-context packages.
