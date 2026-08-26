"""In-memory asynchronous scan jobs for the HTTP boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from inspect import Parameter, signature
import json
import logging
from threading import RLock, Thread
from typing import Any
from uuid import uuid4

from izfin_services.account_data_service import json_uyumlu
from izfin_services.scan_page_state import tarama_sonuc_durumu_hazirla


_UNEXPECTED_SCAN_ERROR = "Tarama işlemi beklenmeyen bir hata nedeniyle tamamlanamadı."
_LOGGER = logging.getLogger(__name__)


class ScanJobCapacityError(RuntimeError):
    """Raised when the in-memory worker or record budget is exhausted."""


@dataclass(frozen=True)
class ScanJobSnapshot:
    job_id: str
    status: str
    stage: str
    completed: int
    total: int
    result: dict[str, Any] | None = None
    error: str | None = None
    tickers: tuple[str, ...] = ()
    created_at: str | None = None
    current_ticker: str | None = None


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
    created_at: str | None = None
    current_ticker: str | None = None

    def snapshot(self) -> ScanJobSnapshot:
        return ScanJobSnapshot(
            job_id=self.job_id,
            status=self.status,
            stage=self.stage,
            completed=self.completed,
            total=len(self.tickers),
            result=self.result.copy() if self.result is not None else None,
            error=self.error,
            tickers=self.tickers,
            created_at=self.created_at,
            current_ticker=self.current_ticker,
        )


class ScanJobStore:
    """Run scan work in a daemon thread and expose owner-isolated snapshots."""

    def __init__(
        self,
        *,
        max_active_jobs: int = 2,
        max_records: int = 100,
        job_repository: Any = None,
    ) -> None:
        if max_active_jobs < 1 or max_records < 1:
            raise ValueError("Job limits must be positive.")
        self._lock = RLock()
        self._records: dict[str, _ScanJobRecord] = {}
        self._max_active_jobs = max_active_jobs
        self._max_records = max_records
        self._job_repository = job_repository

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
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._prune_terminal_records()
            active_jobs = sum(
                existing.status in {"queued", "running"} for existing in self._records.values()
            )
            if active_jobs >= self._max_active_jobs or len(self._records) >= self._max_records:
                raise ScanJobCapacityError("Tarama kuyruğu şu anda dolu.")
            self._records[record.job_id] = record
            self._persist(record)
            created = record.snapshot()
        Thread(
            target=self._execute,
            args=(record.job_id, runner),
            daemon=True,
            name=f"izfin-scan-{record.job_id}",
        ).start()
        return created

    def submit_inline(self, owner_uid: str, tickers: Sequence[str], runner: Callable[..., Mapping[str, Any]]) -> ScanJobSnapshot:
        """Run while the HTTP request owns CPU (request-based Cloud Run safety)."""
        normalized = tuple(str(ticker).strip().upper() for ticker in tickers if str(ticker).strip())
        record = _ScanJobRecord(job_id=str(uuid4()), owner_uid=str(owner_uid), tickers=normalized, created_at=datetime.now(timezone.utc).isoformat())
        with self._lock:
            self._prune_terminal_records()
            active = sum(item.status in {"queued", "running"} for item in self._records.values())
            if active >= self._max_active_jobs or len(self._records) >= self._max_records:
                raise ScanJobCapacityError("Tarama kuyruğu şu anda dolu.")
            self._records[record.job_id] = record
            self._persist(record)
        self._execute(record.job_id, runner)
        return self.get_for_owner(record.job_id, owner_uid) or record.snapshot()

    def get_for_owner(self, job_id: str, owner_uid: str) -> ScanJobSnapshot | None:
        with self._lock:
            record = self._records.get(str(job_id))
            if record is None:
                record = self._restore_terminal_record(str(job_id))
            if record is None or record.owner_uid != str(owner_uid):
                return None
            return record.snapshot()

    def list_for_owner(self, owner_uid: str, *, limit: int = 12) -> list[ScanJobSnapshot]:
        """List recent owner-scoped jobs, including terminal Firestore records."""
        normalized_owner = str(owner_uid)
        bounded_limit = max(1, min(int(limit), 50))
        with self._lock:
            records = {
                job_id: record
                for job_id, record in self._records.items()
                if record.owner_uid == normalized_owner
            }
            repository = self._job_repository
            if getattr(repository, "available", False):
                for data in repository.list_jobs_for_owner(normalized_owner, limit=bounded_limit):
                    job_id = str(data.get("job_id") or "")
                    if not job_id or job_id in records:
                        continue
                    record = self._record_from_data(job_id, data)
                    if record.owner_uid == normalized_owner:
                        self._mark_interrupted(record)
                        self._records[record.job_id] = record
                        records[record.job_id] = record
            ordered = sorted(
                records.values(),
                key=lambda record: record.created_at or "",
                reverse=True,
            )
            return [record.snapshot() for record in ordered[:bounded_limit]]

    def _execute(self, job_id: str, runner: Callable[..., Mapping[str, Any]]) -> None:
        def progress(event: Mapping[str, Any]) -> None:
            self._apply_progress(job_id, event)

        with self._lock:
            record = self._records[job_id]
            record.status = "running"
            record.stage = "starting"
            tickers = record.tickers
            self._persist(record)

        try:
            raw_result = self._run_runner(runner, tickers, progress)
        except Exception:
            with self._lock:
                record = self._records[job_id]
                record.status = "failed"
                record.stage = "failed"
                record.error = _UNEXPECTED_SCAN_ERROR
                self._persist(record)
            return

        presented = tarama_sonuc_durumu_hazirla(raw_result)
        with self._lock:
            record = self._records[job_id]
            record.status = "completed"
            record.stage = "complete"
            record.completed = len(record.tickers)
            record.current_ticker = None
            record.result = json_uyumlu({
                "sonuclar": presented["sonuclar"],
                "teknik_paneller": presented["teknik_paneller"],
                "sozlu_analizler": presented["sozlu_analizler"],
                "basarisiz_taramalar": presented["basarisiz_taramalar"],
                "boga_sayisi": presented["boga_sayisi"],
                "alim_firsati": presented["alim_firsati"],
            })
            self._persist(record)

    @staticmethod
    def _run_runner(
        runner: Callable[..., Mapping[str, Any]],
        tickers: Sequence[str],
        progress_callback: Callable[[Mapping[str, Any]], None],
    ) -> Mapping[str, Any]:
        try:
            parameters = signature(runner).parameters.values()
        except (TypeError, ValueError):
            parameters = ()
        supports_progress = any(
            parameter.name == "progress_callback" or parameter.kind is Parameter.VAR_KEYWORD
            for parameter in parameters
        )
        if supports_progress:
            return runner(tickers, progress_callback=progress_callback)
        return runner(tickers)

    def _prune_terminal_records(self) -> None:
        while len(self._records) >= self._max_records:
            terminal_job_id = next(
                (
                    job_id
                    for job_id, record in self._records.items()
                    if record.status in {"completed", "failed"}
                ),
                None,
            )
            if terminal_job_id is None:
                return
            self._records.pop(terminal_job_id)

    def _apply_progress(self, job_id: str, event: Mapping[str, Any]) -> None:
        stage = str(event.get("stage") or "running")
        with self._lock:
            record = self._records[job_id]
            previous_completed = record.completed
            record.status = "running"
            record.stage = stage
            if stage == "ticker":
                index = int(event.get("index") or 0)
                completed = int(event.get("completed", index) or 0)
                record.completed = min(max(completed, 0), len(record.tickers))
                record.current_ticker = str(event.get("ticker") or "") or None
            elif stage == "finalizing":
                record.completed = len(record.tickers)
                record.current_ticker = None
            elif stage == "complete":
                record.completed = len(record.tickers)
                record.current_ticker = None
            # Ticker-start events are valuable to the open stream but do not
            # need an extra Firestore write. Persist durable phase changes and
            # completed-ticker advances only.
            if stage != "ticker" or record.completed != previous_completed:
                self._persist(record)

    def _persist(self, record: _ScanJobRecord) -> None:
        repository = self._job_repository
        if not getattr(repository, "available", False):
            return
        payload = {
            "job_id": record.job_id,
            "owner_uid": record.owner_uid,
            "tickers": list(record.tickers),
            "status": record.status,
            "stage": record.stage,
            "completed": record.completed,
            # Firestore maps reject some provider-owned nested/scalar values.
            # A JSON string preserves the API contract without asking Firestore
            # to interpret the scan result's internal structure.
            "result_json": (
                json.dumps(record.result, ensure_ascii=False, allow_nan=False)
                if record.result is not None
                else None
            ),
            "error": record.error,
            "created_at": record.created_at,
            "current_ticker": record.current_ticker,
        }
        try:
            repository.upsert_job(record.job_id, payload)
        except Exception:
            # Persistence is durability, not the scan computation itself. Keep
            # the completed in-memory result available to the active request.
            _LOGGER.exception("scan_job_persistence_failed", extra={"scan_job_id": record.job_id})

    def _restore_terminal_record(self, job_id: str) -> _ScanJobRecord | None:
        repository = self._job_repository
        if not getattr(repository, "available", False):
            return None
        data = repository.get_job(job_id)
        if not data:
            return None
        record = self._record_from_data(job_id, data)
        self._mark_interrupted(record)
        self._records[record.job_id] = record
        return record

    @staticmethod
    def _record_from_data(job_id: str, data: Mapping[str, Any]) -> _ScanJobRecord:
        status = str(data.get("status") or "failed")
        result = data.get("result") if isinstance(data.get("result"), dict) else None
        if result is None and isinstance(data.get("result_json"), str):
            try:
                decoded = json.loads(data["result_json"])
                result = decoded if isinstance(decoded, dict) else None
            except (TypeError, ValueError):
                result = None
        return _ScanJobRecord(
            job_id=str(data.get("job_id") or job_id),
            owner_uid=str(data.get("owner_uid") or ""),
            tickers=tuple(str(item) for item in data.get("tickers") or ()),
            status=status,
            stage=str(data.get("stage") or status),
            completed=max(0, int(data.get("completed") or 0)),
            result=result,
            error=str(data.get("error") or "") or None,
            created_at=str(data.get("created_at") or "") or None,
            current_ticker=str(data.get("current_ticker") or "") or None,
        )

    def _mark_interrupted(self, record: _ScanJobRecord) -> None:
        if record.status in {"queued", "running"}:
            record.status = "failed"
            record.stage = "interrupted"
            record.error = "Tarama işlemi uygulama yeniden başlatıldığı için tamamlanamadı."
            self._persist(record)

