from __future__ import annotations

from datetime import datetime

from izfin_services.signal_tracking import sinyal_kayitlarini_guncelle


class FakeRepository:
    def __init__(self):
        self.available = True
        self.archive = {}
        self.active = {}
        self.archive_writes = []
        self.active_writes = []

    def list_archive(self, email, *, limit=500):
        return [(doc_id, data.copy()) for doc_id, data in self.archive.items()]

    def get_active(self, document_id):
        return self.active.get(document_id, {}).copy()

    def set_active(self, document_id, data, *, merge=False):
        current = self.active.get(document_id, {}).copy() if merge else {}
        current.update(data)
        self.active[document_id] = current
        self.active_writes.append((document_id, data.copy(), merge))

    def get_archive(self, document_id):
        return self.archive.get(document_id, {}).copy()

    def set_archive(self, document_id, data, *, merge=False):
        current = self.archive.get(document_id, {}).copy() if merge else {}
        current.update(data)
        self.archive[document_id] = current
        self.archive_writes.append((document_id, data.copy(), merge))


def _now():
    return datetime(2026, 8, 23, 23, 45, 0, 123456)


def _yon(sinyal):
    return "ALIM" if "AL" in str(sinyal).upper() else "NÖTR"


def _panel(fiyat=100.0):
    return {
        "fiyat": fiyat,
        "stop": 94.0,
        "tp1": 108.0,
        "tp2": 115.0,
        "tp3": 123.0,
        "rsi": 58.0,
        "teyit": "Güçlü teyit",
        "tetik_puani": 76,
        "giris_puani": 79,
        "cezali_skor": 82,
        "guven_skoru": 84,
        "veri_kaynagi": "Yahoo",
        "peg": 1.4,
        "sektorel_fark": 3.2,
    }


def test_unavailable_or_anonymous_repository_is_noop():
    repo = FakeRepository()
    repo.available = False
    ozet = sinyal_kayitlarini_guncelle(
        [{"Varlık": "NVDA", "Nihai Sinyal": "AL 🟢"}],
        {"NVDA": _panel()},
        repository=repo,
        user_email="user@example.com",
        strategy_version="v-test",
        signal_direction_resolver=_yon,
        now_factory=_now,
    )
    assert ozet["islenen"] == 0
    assert repo.archive_writes == []


def test_new_buy_signal_opens_period_and_freezes_entry_context():
    repo = FakeRepository()
    ozet = sinyal_kayitlarini_guncelle(
        [{"Varlık": "NVDA", "Nihai Sinyal": "AL 🟢"}],
        {"NVDA": _panel(100.0)},
        repository=repo,
        user_email="user@example.com",
        strategy_version="v-test",
        signal_direction_resolver=_yon,
        now_factory=_now,
    )

    assert ozet["acilan"] == 1
    assert len(repo.archive) == 1
    doc_id, veri = next(iter(repo.archive.items()))
    assert veri["giris_fiyati"] == 100.0
    assert veri["ilk_sinyal"] == "AL 🟢"
    assert veri["ilk_stop"] == 94.0
    assert veri["ilk_giris_kalitesi"] == 79
    assert veri["strategy_version"] == "v-test"
    assert veri["benchmark_ticker"] == "^IXIC"
    aktif_id = "user_example_com_NVDA"
    assert repo.active[aktif_id]["arsiv_doc_id"] == doc_id
    assert repo.active[aktif_id]["giris_fiyati"] == 100.0


def test_same_signal_does_not_rewrite_open_period():
    repo = FakeRepository()
    aktif_id = "user_example_com_NVDA"
    repo.active[aktif_id] = {
        "durum": "ACIK",
        "sinyal": "AL 🟢",
        "arsiv_doc_id": "arc-1",
        "giris_fiyati": 90.0,
        "sinyal_degisim_sayisi": 0,
    }
    repo.archive["arc-1"] = {
        "user_email": "user@example.com",
        "ticker": "NVDA",
        "yon": "ALIM",
        "durum": "ACIK",
        "sinyal": "AL 🟢",
        "giris_fiyati": 90.0,
        "olusturma_zamani": "2026-08-01T10:00:00",
    }

    sinyal_kayitlarini_guncelle(
        [{"Varlık": "NVDA", "Nihai Sinyal": "AL 🟢"}],
        {"NVDA": _panel(110.0)},
        repository=repo,
        user_email="user@example.com",
        strategy_version="v-test",
        signal_direction_resolver=_yon,
        now_factory=_now,
    )

    assert repo.archive_writes == []
    assert repo.active_writes == []
    assert repo.active[aktif_id]["giris_fiyati"] == 90.0


def test_signal_change_updates_existing_period_without_new_entry():
    repo = FakeRepository()
    aktif_id = "user_example_com_NVDA"
    repo.active[aktif_id] = {
        "durum": "ACIK",
        "sinyal": "ERKEN AL 🟢",
        "arsiv_doc_id": "arc-1",
        "giris_fiyati": 90.0,
        "sinyal_degisim_sayisi": 2,
    }
    repo.archive["arc-1"] = {
        "user_email": "user@example.com",
        "ticker": "NVDA",
        "yon": "ALIM",
        "durum": "ACIK",
        "sinyal": "ERKEN AL 🟢",
        "giris_fiyati": 90.0,
        "olusturma_zamani": "2026-08-01T10:00:00",
    }

    ozet = sinyal_kayitlarini_guncelle(
        [{"Varlık": "NVDA", "Nihai Sinyal": "AL 🟢"}],
        {"NVDA": _panel(112.0)},
        repository=repo,
        user_email="user@example.com",
        strategy_version="v-test",
        signal_direction_resolver=_yon,
        now_factory=_now,
    )

    assert ozet["guncellenen"] == 1
    assert len(repo.archive) == 1
    assert repo.archive["arc-1"]["onceki_sinyal"] == "ERKEN AL 🟢"
    assert repo.archive["arc-1"]["sinyal_degisim_sayisi"] == 3
    assert repo.active[aktif_id]["giris_fiyati"] == 90.0


def test_legacy_open_archive_is_relinked_instead_of_opening_duplicate():
    repo = FakeRepository()
    repo.archive["legacy-old"] = {
        "user_email": "user@example.com",
        "ticker": "THYAO.IS",
        "yon": "ALIM",
        "durum": "ACIK",
        "sinyal": "AL 🟢",
        "giris_fiyati": 320.0,
        "olusturma_zamani": "2026-07-01T10:00:00",
    }

    ozet = sinyal_kayitlarini_guncelle(
        [{"Varlık": "THYAO.IS", "Nihai Sinyal": "AL 🟢"}],
        {"THYAO.IS": _panel(350.0)},
        repository=repo,
        user_email="user@example.com",
        strategy_version="v-test",
        signal_direction_resolver=_yon,
        now_factory=_now,
    )

    assert ozet["yeniden_baglanan"] == 1
    assert ozet["acilan"] == 0
    aktif_id = "user_example_com_THYAO_IS"
    assert repo.active[aktif_id]["arsiv_doc_id"] == "legacy-old"
    assert repo.active[aktif_id]["giris_fiyati"] == 320.0
    assert len(repo.archive) == 1


def test_non_buy_signal_closes_open_period_with_period_stats():
    repo = FakeRepository()
    aktif_id = "user_example_com_NVDA"
    repo.active[aktif_id] = {
        "durum": "ACIK",
        "sinyal": "AL 🟢",
        "arsiv_doc_id": "arc-1",
        "giris_fiyati": 100.0,
        "acilis_zamani": "2026-08-01T10:00:00",
    }
    repo.archive["arc-1"] = {
        "user_email": "user@example.com",
        "ticker": "NVDA",
        "yon": "ALIM",
        "durum": "ACIK",
        "giris_fiyati": 100.0,
        "olusturma_zamani": "2026-08-01T10:00:00",
        "ilk_stop": 94.0,
        "ilk_tp1": 108.0,
        "ilk_tp2": 115.0,
        "ilk_tp3": 123.0,
    }
    calls = []

    def stats(*args):
        calls.append(args)
        return {"max_getiri_yuzde": 18.5, "min_getiri_yuzde": -3.0}

    ozet = sinyal_kayitlarini_guncelle(
        [{"Varlık": "NVDA", "Nihai Sinyal": "Nötr (İzle)"}],
        {"NVDA": _panel(110.0)},
        repository=repo,
        user_email="user@example.com",
        strategy_version="v-test",
        signal_direction_resolver=_yon,
        period_stats_resolver=stats,
        now_factory=_now,
    )

    assert ozet["kapanan"] == 1
    assert calls
    assert repo.archive["arc-1"]["durum"] == "KAPALI"
    assert repo.archive["arc-1"]["getiri_yuzde"] == 10.0
    assert repo.archive["arc-1"]["max_getiri_yuzde"] == 18.5
    assert repo.active[aktif_id]["durum"] == "KAPALI"
    assert repo.active[aktif_id]["arsiv_doc_id"] is None
