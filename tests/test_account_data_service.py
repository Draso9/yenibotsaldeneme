from __future__ import annotations

from datetime import datetime, timezone
import json
import math

from izfin_services.account_data_service import (
    ACCOUNT_DELETE_CONFIRMATION_ERROR,
    AccountDataService,
    hesap_silme_onayi_dogrula,
    json_uyumlu,
)


class FakeRepository:
    def __init__(self, *, available=True):
        self.available = available
        self.collected = []
        self.deleted = []
        self.documents = [
            {
                "collection": "kullanicilar",
                "document_id": "uid-1",
                "data": {"created_at": datetime(2026, 8, 24, tzinfo=timezone.utc)},
            },
            {
                "collection": "kullanici_listeleri",
                "document_id": "uid-1",
                "data": {"tickers": {"NVDA", "AAPL"}},
            },
        ]

    def collect_user_documents(self, uid, email):
        self.collected.append((uid, email))
        return list(self.documents)

    def delete_documents(self, documents):
        self.deleted.append(list(documents))


def _service(repo=None, *, revoke=None, delete=None, errors=None):
    errors = errors if errors is not None else []
    return AccountDataService(
        repo or FakeRepository(),
        revoke_refresh_tokens=revoke or (lambda _uid: None),
        delete_user=delete or (lambda _uid: None),
        app_release="1.9.1",
        now_factory=lambda: datetime(2026, 8, 24, 12, 30, tzinfo=timezone.utc),
        error_handler=lambda context, error: errors.append((context, str(error))),
    )


def test_json_compatible_conversion_handles_nested_provider_values():
    converted = json_uyumlu(
        {
            "nan": math.nan,
            "when": datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc),
            "raw": b"\x01\xff",
            "items": (1, {2, 3}),
        }
    )
    assert converted["nan"] is None
    assert converted["when"] == "2026-08-24T12:00:00+00:00"
    assert converted["raw"] == "01ff"
    assert converted["items"][0] == 1
    assert set(converted["items"][1]) == {2, 3}


def test_export_package_groups_documents_and_serializes_as_utf8_json():
    repo = FakeRepository()
    service = _service(repo)

    package = service.veri_paketi_olustur(uid=" uid-1 ", email=" USER@EXAMPLE.COM ")
    payload = service.veri_paketi_json_olustur(uid="uid-1", email="user@example.com")

    assert repo.collected == [
        ("uid-1", "user@example.com"),
        ("uid-1", "user@example.com"),
    ]
    assert package["export_schema"] == "izfin-user-data-v1"
    assert package["app_release"] == "1.9.1"
    assert package["exported_at"] == "2026-08-24T12:30:00+00:00"
    assert package["collections"]["kullanicilar"][0]["document_id"] == "uid-1"
    decoded = json.loads(payload)
    assert decoded["user_email"] == "user@example.com"
    assert set(decoded["collections"]["kullanici_listeleri"][0]["data"]["tickers"]) == {
        "NVDA",
        "AAPL",
    }


def test_account_deletion_revokes_and_deletes_auth_after_documents():
    repo = FakeRepository()
    calls = []
    service = _service(
        repo,
        revoke=lambda uid: calls.append(("revoke", uid)),
        delete=lambda uid: calls.append(("delete", uid)),
    )

    count = service.hesabi_kalici_sil(uid="uid-1", email="USER@EXAMPLE.COM")

    assert count == 2
    assert len(repo.deleted[0]) == 2
    assert calls == [("revoke", "uid-1"), ("delete", "uid-1")]


def test_account_deletion_logs_revoke_failure_but_still_removes_auth_user():
    errors = []
    deleted = []

    def fail_revoke(_uid):
        raise RuntimeError("revoke failed")

    service = _service(
        revoke=fail_revoke,
        delete=lambda uid: deleted.append(uid),
        errors=errors,
    )
    assert service.hesabi_kalici_sil(uid="uid-1", email="u@example.com") == 2
    assert deleted == ["uid-1"]
    assert errors == [("hesap_sil_token_iptali", "revoke failed")]


def test_account_identity_and_irreversible_confirmation_guards():
    unavailable = _service(FakeRepository(available=False))
    try:
        unavailable.veri_paketi_olustur(uid="uid", email="u@example.com")
    except RuntimeError as error:
        assert str(error) == "Firebase veritabanı bağlantısı kullanılamıyor."
    else:
        raise AssertionError("unavailable repository must be rejected")

    assert hesap_silme_onayi_dogrula(
        hesap_email="User@Example.com",
        girilen_email=" user@example.com ",
        girilen_ifade="HESABIMI KALICI OLARAK SİL",
        geri_alinamaz=True,
    ) == (True, None)
    assert hesap_silme_onayi_dogrula(
        hesap_email="user@example.com",
        girilen_email="wrong@example.com",
        girilen_ifade="HESABIMI KALICI OLARAK SİL",
        geri_alinamaz=True,
    ) == (False, ACCOUNT_DELETE_CONFIRMATION_ERROR)
