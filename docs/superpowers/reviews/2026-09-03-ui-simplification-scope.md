# UI simplification scope

Approved user-visible scope only:

- Keep scan controls available but progressively disclose them; first-use scanning remains open, completed-result context moves them to the background.
- Move the stock-specific Decision Motor before mobile and desktop result tables.
- Keep only central verdict, positive reason, risk/wait reason, and stop visible by default.
- Move confidence, entry quality, MTF, technical profile, explanations, support/resistance, and targets into a collapsed detail area.
- Make Detailed Analysis start with a compact technical summary, then expose indicators, trend/momentum, levels/entry, and targets/algorithmic commentary as separate collapsed groups.
- Do not change financial calculations, decision rules, API payloads, auth, recovery, or shared ticker continuity.

TDD: `tests/test_ui_simplification_contract.py` is the RED contract and must fail before production UI changes are added.
