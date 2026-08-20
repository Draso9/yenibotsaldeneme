"""Aktif sinyal, pozisyon arşivi ve performans kaydı erişimi."""

from __future__ import annotations


class SignalRepository:
    def __init__(self, db):
        self.db = db

    @property
    def available(self):
        return self.db is not None

    def list_archive(self, email, *, limit=500):
        query = (
            self.db.collection("sinyal_arsivi")
            .where("user_email", "==", email)
            .limit(limit)
        )
        return [(doc.id, doc.to_dict() or {}) for doc in query.stream()]

    def list_performance_records(self, email, *, limit=250):
        records = []
        for doc_id, data in self.list_archive(email, limit=limit):
            if data.get("yon") != "ALIM":
                continue
            records.append({**data, "doc_id": doc_id})
        records.sort(key=lambda item: item.get("olusturma_zamani", ""), reverse=True)
        return records

    def get_active(self, document_id):
        snapshot = self.db.collection("aktif_sinyaller").document(document_id).get()
        return (snapshot.to_dict() or {}) if snapshot.exists else {}

    def set_active(self, document_id, data, *, merge=False):
        self.db.collection("aktif_sinyaller").document(document_id).set(
            data,
            merge=merge,
        )

    def get_archive(self, document_id):
        snapshot = self.db.collection("sinyal_arsivi").document(document_id).get()
        return (snapshot.to_dict() or {}) if snapshot.exists else {}

    def set_archive(self, document_id, data, *, merge=False):
        self.db.collection("sinyal_arsivi").document(document_id).set(
            data,
            merge=merge,
        )

    def delete_archive(self, document_id):
        self.db.collection("sinyal_arsivi").document(document_id).delete()

    def backup_archive(self, document_id, data):
        self.db.collection("sinyal_arsivi_temizlik_yedegi").document(
            document_id
        ).set(data)
