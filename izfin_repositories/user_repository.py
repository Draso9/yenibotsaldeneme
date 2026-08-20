"""Kullanıcı profili, kişisel liste ve veri yaşam döngüsü erişimi."""

from __future__ import annotations


class UserRepository:
    def __init__(self, db):
        self.db = db

    @property
    def available(self):
        return self.db is not None

    def upsert_profile(self, uid, data, *, merge=True):
        self.db.collection("kullanicilar").document(uid).set(data, merge=merge)

    def get_profile(self, uid):
        snapshot = self.db.collection("kullanicilar").document(uid).get()
        return (snapshot.to_dict() or {}) if snapshot.exists else {}

    def upsert_watchlist(self, document_id, data, *, merge=True):
        self.db.collection("kullanici_listeleri").document(document_id).set(
            data,
            merge=merge,
        )

    def get_watchlist(self, document_id):
        snapshot = self.db.collection("kullanici_listeleri").document(document_id).get()
        if not snapshot.exists:
            return False, {}
        return True, snapshot.to_dict() or {}

    def get_primary_and_legacy_watchlists(self, primary_id, legacy_id=None):
        primary_exists, primary_data = self.get_watchlist(primary_id)
        legacy_exists = False
        legacy_data = {}
        if legacy_id and legacy_id != primary_id:
            try:
                legacy_exists, legacy_data = self.get_watchlist(legacy_id)
            except Exception:
                legacy_exists, legacy_data = False, {}
        return {
            "primary_exists": primary_exists,
            "primary_data": primary_data,
            "legacy_exists": legacy_exists,
            "legacy_data": legacy_data,
        }

    def collect_user_documents(self, uid, email):
        bulunan = {}

        def ekle(koleksiyon, snapshot):
            if snapshot is not None and snapshot.exists:
                bulunan[(koleksiyon, snapshot.id)] = snapshot.to_dict() or {}

        ekle("kullanicilar", self.db.collection("kullanicilar").document(uid).get())
        ekle(
            "kullanici_listeleri",
            self.db.collection("kullanici_listeleri").document(uid).get(),
        )
        if email != uid:
            ekle(
                "kullanici_listeleri",
                self.db.collection("kullanici_listeleri").document(email).get(),
            )

        for koleksiyon in (
            "sinyal_arsivi",
            "aktif_sinyaller",
            "sinyal_arsivi_temizlik_yedegi",
        ):
            sorgu = self.db.collection(koleksiyon).where("user_email", "==", email)
            for snapshot in sorgu.stream():
                ekle(koleksiyon, snapshot)

        email_anahtari = email.replace("@", "_").replace(".", "_")
        arsiv_tickerlari = {
            str(veri.get("ticker") or "").strip()
            for (koleksiyon, _), veri in bulunan.items()
            if koleksiyon == "sinyal_arsivi" and str(veri.get("ticker") or "").strip()
        }
        for ticker in arsiv_tickerlari:
            aktif_id = f"{email_anahtari}_{ticker.replace('.', '_')}"
            ekle(
                "aktif_sinyaller",
                self.db.collection("aktif_sinyaller").document(aktif_id).get(),
            )

        return [
            {"collection": koleksiyon, "document_id": doc_id, "data": veri}
            for (koleksiyon, doc_id), veri in sorted(bulunan.items())
        ]

    def delete_documents(self, documents, *, batch_size=400):
        for baslangic in range(0, len(documents), batch_size):
            batch = self.db.batch()
            for belge in documents[baslangic : baslangic + batch_size]:
                ref = self.db.collection(belge["collection"]).document(
                    belge["document_id"]
                )
                batch.delete(ref)
            batch.commit()
