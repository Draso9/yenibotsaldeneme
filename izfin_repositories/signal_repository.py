"""Aktif sinyal, pozisyon arşivi ve performans kaydı erişimi."""

from __future__ import annotations


class ScanJobRepository:
    """Firestore persistence for owner-isolated API scan-job snapshots."""

    COLLECTION = "izfin_scan_jobs"

    def __init__(self, db):
        self.db = db

    @property
    def available(self):
        return self.db is not None

    def get_job(self, job_id):
        snapshot = self.db.collection(self.COLLECTION).document(str(job_id)).get()
        return (snapshot.to_dict() or {}) if snapshot.exists else {}

    def upsert_job(self, job_id, data):
        self.db.collection(self.COLLECTION).document(str(job_id)).set(dict(data), merge=True)

    def list_jobs_for_owner(self, owner_uid, *, limit=20):
        query = (
            self.db.collection(self.COLLECTION)
            .where("owner_uid", "==", str(owner_uid))
            .limit(max(1, min(int(limit), 50)))
        )
        records = [doc.to_dict() or {} for doc in query.stream()]
        return sorted(records, key=lambda item: str(item.get("created_at") or ""), reverse=True)


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
