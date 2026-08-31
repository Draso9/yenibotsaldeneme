from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1]


def _run_node(script: str) -> dict[str, object]:
    executed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert executed.returncode == 0, executed.stderr
    return json.loads(executed.stdout)


def test_account_profile_summary_formats_existing_profile_timestamps():
    """Dropping either stored profile timestamp must remove visible account history."""
    payload = _run_node(
        """
import { accountProfileSummary } from "./web/lib/account-presentation.mjs";

console.log(JSON.stringify(accountProfileSummary({
  email: "stored@example.com",
  olusturma_zamani: "2026-08-24T10:15:00",
  son_giris: "2026-08-30T14:05:00",
}, "identity@example.com")));
"""
    )

    assert payload == {
        "email": "identity@example.com",
        "createdAt": "24 Ağustos 2026 · 10:15",
        "lastLogin": "30 Ağustos 2026 · 14:05",
    }


def test_account_profile_summary_uses_real_firebase_metadata_when_profile_is_legacy_empty():
    """Web-created accounts must not invent dates when stored profile history is absent."""
    payload = _run_node(
        """
import { accountProfileSummary } from "./web/lib/account-presentation.mjs";

console.log(JSON.stringify(accountProfileSummary(
  {},
  "identity@example.com",
  {
    creationTime: "Sun, 24 Aug 2026 10:15:00 GMT",
    lastSignInTime: "Sun, 30 Aug 2026 14:05:00 GMT",
  },
)));
"""
    )

    assert payload == {
        "email": "identity@example.com",
        "createdAt": "24 Ağustos 2026 · 10:15",
        "lastLogin": "30 Ağustos 2026 · 14:05",
    }


def test_admin_readiness_cards_preserve_each_authoritative_runtime_boundary():
    """A degraded dependency must remain visible instead of becoming a fake green state."""
    payload = _run_node(
        """
import { readinessCards, readinessHeadline } from "./web/lib/admin-quality-presentation.mjs";

const readiness = {
  ready: false,
  authentication: true,
  user_repository: true,
  signal_repository: false,
  scan_runner: true,
  scan_job_store: true,
  scan_job_persistence: false,
};
console.log(JSON.stringify({
  headline: readinessHeadline(readiness),
  cards: readinessCards(readiness),
  pendingCards: readinessCards(null),
}));
"""
    )

    assert payload == {
        "headline": "Bazı çekirdek servisler kısıtlı",
        "pendingCards": [],
        "cards": [
            {"label": "Kimlik doğrulama", "ready": True},
            {"label": "Kullanıcı deposu", "ready": True},
            {"label": "Sinyal deposu", "ready": False},
            {"label": "Tarama motoru", "ready": True},
            {"label": "Tarama iş deposu", "ready": True},
            {"label": "Kalıcı tarama kaydı", "ready": False},
        ],
    }
