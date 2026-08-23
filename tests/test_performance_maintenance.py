from __future__ import annotations

from datetime import datetime

from izfin_services.performance_maintenance import gecmis_mukerrer_kayitlari_temizle


class FakeRepository:
    def __init__(self):
        self.available = True
        self.archive = {}
        self.backups = {}
        self.deleted = []
        self.active = {}

    def list_archive(self, email, *, limit=1000):
        return [(doc_id, data.copy()) for doc_id, data in self.archive.items()]

    def backup_archive(self, document_id, data):
        self.backups[document_id] = data.copy()

    def delete_archive(self, document_id):
        self.deleted.append(document_id)
        self.archive.pop(document_id, None)

    def set_active(self, document_id, data, *, merge=False):
        current = self.active.get(document_id, {}).copy() if merge else {}
        current.update(data)
        self.active[document_id] = current


def _now():
    return datetime(2026, 8, 23, 23, 55, 1, 123456)


def test_unavailable_or_anonymous_is_noop():
    repo = FakeRepository()
    repo.available = False
    assert gecmis_mukerrer_kayitlari_temizle(
        repository=repo,
        user_email="user@example.com",
        now_factory=_now,
    ) == {"silinen": 0, "yedeklenen": 0, "grup": 0}


def test_open_duplicates_keep_oldest_and_rebind_active_document():
    repo = FakeRepository()
    repo.archive = {
        "newer": {
            "user_email": "user@example.com",
            "ticker": "NVDA",
            "yon": "ALIM",
            "durum": "ACIK",
            "olusturma_zamani": "2026-08-10T10:00:00",
            "giris_fiyati": 120.0,
        },
        "oldest": {
            "user_email": "user@example.com",
            "ticker": "NVDA",
            "yon": "ALIM",
            "durum": "ACIK",
            "olusturma_zamani": "2026-08-01T10:00:00",
            "giris_fiyati": 100.0,
        },
    }

    ozet = gecmis_mukerrer_kayitlari_temizle(
        repository=repo,
        user_email="user@example.com",
        now_factory=_now,
    )

    assert ozet == {"silinen": 1, "yedeklenen": 1, "grup": 1}
    assert "oldest" in repo.archive
    assert "newer" not in repo.archive
    backup = next(iter(repo.backups.values()))
    assert backup["orijinal_doc_id"] == "newer"
    assert backup["korunan_doc_id"] == "oldest"
    assert backup["temizlik_nedeni"] == "gecmis_mukerrer_kayit"
    assert repo.active["user_example_com_NVDA"]["arsiv_doc_id"] == "oldest"


def test_closed_duplicates_keep_richer_document():
    repo = FakeRepository()
    common = {
        "user_email": "user@example.com",
        "ticker": "THYAO.IS",
        "yon": "ALIM",
        "durum": "KAPALI",
        "olusturma_zamani": "2026-08-01T10:00:15",
        "kapanis_zamani": "2026-08-10T15:30:20",
        "giris_fiyati": 300.123456,
    }
    repo.archive = {
        "sparse": {**common, "tp1": None},
        "rich": {**common, "tp1": 320.0, "tp2": 335.0, "max_getiri_yuzde": 12.0},
    }

    ozet = gecmis_mukerrer_kayitlari_temizle(
        repository=repo,
        user_email="user@example.com",
        now_factory=_now,
    )

    assert ozet["grup"] == 1
    assert repo.deleted == ["sparse"]
    assert "rich" in repo.archive
    assert repo.active == {}


def test_non_buy_records_are_not_touched():
    repo = FakeRepository()
    repo.archive = {
        "one": {"ticker": "NVDA", "yon": "SATIM", "durum": "ACIK"},
        "two": {"ticker": "NVDA", "yon": "SATIM", "durum": "ACIK"},
    }
    ozet = gecmis_mukerrer_kayitlari_temizle(
        repository=repo,
        user_email="user@example.com",
        now_factory=_now,
    )
    assert ozet == {"silinen": 0, "yedeklenen": 0, "grup": 0}
    assert repo.deleted == []


def test_read_error_returns_zero_summary_and_reports_context():
    class BrokenRepository(FakeRepository):
        def list_archive(self, email, *, limit=1000):
            raise RuntimeError("boom")

    errors = []
    ozet = gecmis_mukerrer_kayitlari_temizle(
        repository=BrokenRepository(),
        user_email="user@example.com",
        error_handler=lambda context, error, *args, **kwargs: errors.append(context),
        now_factory=_now,
    )
    assert ozet == {"silinen": 0, "yedeklenen": 0, "grup": 0}
    assert errors == ["gecmis_kayit_temizlik_okuma"]
