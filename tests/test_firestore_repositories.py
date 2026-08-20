from __future__ import annotations

from copy import deepcopy

from izfin_repositories.signal_repository import SignalRepository
from izfin_repositories.user_repository import UserRepository


class FakeSnapshot:
    def __init__(self, document_id, data):
        self.id = document_id
        self._data = deepcopy(data) if data is not None else None
        self.exists = data is not None

    def to_dict(self):
        return deepcopy(self._data)


class FakeDocument:
    def __init__(self, collection, document_id):
        self.collection = collection
        self.id = document_id

    def get(self):
        return FakeSnapshot(self.id, self.collection.documents.get(self.id))

    def set(self, data, merge=False):
        if merge and self.id in self.collection.documents:
            self.collection.documents[self.id].update(deepcopy(data))
        else:
            self.collection.documents[self.id] = deepcopy(data)

    def delete(self):
        self.collection.documents.pop(self.id, None)


class FakeQuery:
    def __init__(self, collection, filters=None, limit_value=None):
        self.collection = collection
        self.filters = list(filters or [])
        self.limit_value = limit_value

    def where(self, field, operator, value):
        assert operator == "=="
        return FakeQuery(
            self.collection,
            [*self.filters, (field, value)],
            self.limit_value,
        )

    def limit(self, value):
        return FakeQuery(self.collection, self.filters, value)

    def stream(self):
        rows = []
        for document_id, data in self.collection.documents.items():
            if all(data.get(field) == value for field, value in self.filters):
                rows.append(FakeSnapshot(document_id, data))
        return rows[: self.limit_value]


class FakeCollection(FakeQuery):
    def __init__(self, documents=None):
        self.documents = deepcopy(documents or {})
        super().__init__(self)

    def document(self, document_id):
        return FakeDocument(self, document_id)


class FakeBatch:
    def __init__(self):
        self.pending = []
        self.committed = False

    def delete(self, reference):
        self.pending.append(reference)

    def commit(self):
        for reference in self.pending:
            reference.delete()
        self.committed = True


class FakeDB:
    def __init__(self, initial=None):
        self.collections = {
            name: FakeCollection(documents)
            for name, documents in (initial or {}).items()
        }
        self.batches = []

    def collection(self, name):
        return self.collections.setdefault(name, FakeCollection())

    def batch(self):
        batch = FakeBatch()
        self.batches.append(batch)
        return batch


def test_user_repository_profile_and_watchlist_contract():
    db = FakeDB()
    repository = UserRepository(db)

    repository.upsert_profile("uid-1", {"email": "a@example.com"})
    repository.upsert_profile("uid-1", {"son_giris": "now"})
    repository.upsert_watchlist("uid-1", {"tickers": ["AAPL"]})

    assert repository.get_profile("uid-1") == {
        "email": "a@example.com",
        "son_giris": "now",
    }
    assert repository.get_watchlist("uid-1") == (True, {"tickers": ["AAPL"]})
    assert repository.get_watchlist("missing") == (False, {})


def test_user_repository_returns_primary_and_legacy_watchlists():
    db = FakeDB(
        {
            "kullanici_listeleri": {
                "uid-1": {"tickers": ["AAPL"]},
                "a@example.com": {"tickers": ["THYAO.IS"]},
            }
        }
    )
    result = UserRepository(db).get_primary_and_legacy_watchlists(
        "uid-1",
        "a@example.com",
    )

    assert result == {
        "primary_exists": True,
        "primary_data": {"tickers": ["AAPL"]},
        "legacy_exists": True,
        "legacy_data": {"tickers": ["THYAO.IS"]},
    }


def test_user_repository_collects_export_scope_and_legacy_active_document():
    email = "a@example.com"
    active_id = "a_example_com_AAPL"
    db = FakeDB(
        {
            "kullanicilar": {"uid-1": {"uid": "uid-1", "email": email}},
            "kullanici_listeleri": {
                "uid-1": {"tickers": ["AAPL"]},
                email: {"tickers": ["THYAO.IS"]},
            },
            "sinyal_arsivi": {
                "archive-1": {"user_email": email, "ticker": "AAPL"},
                "other": {"user_email": "other@example.com", "ticker": "MSFT"},
            },
            "aktif_sinyaller": {
                active_id: {"ticker": "AAPL"},
            },
            "sinyal_arsivi_temizlik_yedegi": {
                "backup-1": {"user_email": email, "ticker": "AAPL"},
            },
        }
    )

    documents = UserRepository(db).collect_user_documents("uid-1", email)
    keys = {(item["collection"], item["document_id"]) for item in documents}

    assert keys == {
        ("kullanicilar", "uid-1"),
        ("kullanici_listeleri", "uid-1"),
        ("kullanici_listeleri", email),
        ("sinyal_arsivi", "archive-1"),
        ("aktif_sinyaller", active_id),
        ("sinyal_arsivi_temizlik_yedegi", "backup-1"),
    }


def test_user_repository_deletes_documents_in_batches():
    db = FakeDB({"kullanicilar": {"a": {"x": 1}, "b": {"x": 2}, "c": {"x": 3}}})
    documents = [
        {"collection": "kullanicilar", "document_id": key, "data": {}}
        for key in ("a", "b", "c")
    ]

    UserRepository(db).delete_documents(documents, batch_size=2)

    assert db.collection("kullanicilar").documents == {}
    assert len(db.batches) == 2
    assert all(batch.committed for batch in db.batches)


def test_signal_repository_crud_and_performance_sort_contract():
    email = "a@example.com"
    db = FakeDB(
        {
            "sinyal_arsivi": {
                "old": {
                    "user_email": email,
                    "yon": "ALIM",
                    "olusturma_zamani": "2026-01-01",
                },
                "new": {
                    "user_email": email,
                    "yon": "ALIM",
                    "olusturma_zamani": "2026-02-01",
                },
                "ignored": {
                    "user_email": email,
                    "yon": "SATIŞ",
                    "olusturma_zamani": "2026-03-01",
                },
            }
        }
    )
    repository = SignalRepository(db)

    repository.set_active("active-1", {"durum": "ACIK"})
    repository.set_active("active-1", {"sinyal": "Güçlü Al"}, merge=True)
    repository.set_archive("new", {"son_fiyat": 12.0}, merge=True)

    records = repository.list_performance_records(email)
    assert [record["doc_id"] for record in records] == ["new", "old"]
    assert repository.get_active("active-1") == {
        "durum": "ACIK",
        "sinyal": "Güçlü Al",
    }
    assert repository.get_archive("new")["son_fiyat"] == 12.0


def test_signal_repository_backup_and_delete_contract():
    db = FakeDB({"sinyal_arsivi": {"archive-1": {"ticker": "AAPL"}}})
    repository = SignalRepository(db)

    repository.backup_archive("backup-1", {"orijinal_doc_id": "archive-1"})
    repository.delete_archive("archive-1")

    assert repository.get_archive("archive-1") == {}
    assert db.collection("sinyal_arsivi_temizlik_yedegi").documents == {
        "backup-1": {"orijinal_doc_id": "archive-1"}
    }
