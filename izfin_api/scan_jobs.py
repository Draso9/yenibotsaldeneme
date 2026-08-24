"""In-memory asynchronous scan jobs for the HTTP boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from threading import RLock, Thread
from typing import Any
from uuid import uuid4

from izfin_services.scan_page_state import tarama_sonuc_durumu_hazirla


_UNEXPECTED_SCAN_ERROR = "Tarama işlemi beklenmeyen bir hata nedeniyle tamamlanamadı."


@dataclass(frozen=True)
class ScanJobSnapshot:
    job_id: str
    status: str
    stage: str
    completed: int
    total: int
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class _ScanJobRecord:
    job_id: str
    owner_uid: str
    tickers: tuple[str, ...]
    status: str = "queued"
    stage: str = "queued"
    completed: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None

    def snapshot(self) -> ScanJobSnapshot:
        return ScanJobSnapshot(
            job_id=self.job_id,
            status=self.status,
            stage=self.stage,
            completed=self.completed,
            total=len(self.tickers),
            result=self.result.copy() if self.result is not None else None,
            error=self.error,
        )


class ScanJobStore:
    """Run scan work in a daemon thread and expose owner-isolated snapshots."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[str, _ScanJobRecord] = {}

    def submit(
        self,
        owner_uid: str,
        tickers: Sequence[str],
        runner: Callable[..., Mapping[str, Any]],
    ) -> ScanJobSnapshot:
        normalized_tickers = tuple(str(ticker).strip().upper() for ticker in tickers if str(ticker).strip())
        record = _ScanJobRecord(
            job_id=str(uuid4()),
            owner_uid=str(owner_uid),
            tickers=normalized_tickers,
        )
        with self._lock:
            self._records[record.job_id] = record
            created = record.snapshot()
        Thread(
            target=self._execute,
            args=(record.job_id, runner),
            daemon=True,
            name=f"izfin-scan-{record.job_id}",
        ).start()
        return created

    def get_for_owner(self, job_id: str, owner_uid: str) -> ScanJobSnapshot | None:
        with self._lock:
            record = self._records.get(str(job_id))
            if record is None or record.owner_uid != str(owner_uid):
                return None
            return record.snapshot()

    def _execute(self, job_id: str, runner: Callable[..., Mapping[str, Any]]) -> None:
        def progress(event: Mapping[str, Any]) -> None:
            self._apply_progress(job_id, event)

        with self._lock:
            record = self._records[job_id]
            record.status = "running"
            record.stage = "starting"
            tickers = record.tickers

        try:
            raw_result = runner(tickers, progress_callback=progress)
        except Exception:
            with self._lock:
                record = self._records[job_id]
                record.status = "failed"
                record.stage = "failed"
                record.error = _UNEXPECTED_SCAN_ERROR
            return

        presented = tarama_sonuc_durumu_hazirla(raw_result)
        with self._lock:
            record = self._records[job_id]
            record.status = "completed"
            record.stage = "complete"
            record.completed = len(record.tickers)
            record.result = {
                "sonuclar": presented["sonuclar"],
                "basarisiz_taramalar": presented["basarisiz_taramalar"],
                "boga_sayisi": presented["boga_sayisi"],
                "alim_firsati": presented["alim_firsati"],
            }

    def _apply_progress(self, job_id: str, event: Mapping[str, Any]) -> None:
        stage = str(event.get("stage") or "running")
        with self._lock:
            record = self._records[job_id]
            record.status = "running"
            record.stage = stage
            if stage == "ticker":
                index = int(event.get("index") or 0)
                record.completed = min(max(index, 0), len(record.tickers))
            elif stage == "complete":
                record.completed = len(record.tickers)
