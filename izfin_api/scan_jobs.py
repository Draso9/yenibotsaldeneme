"""In-memory asynchronous scan jobs for the HTTP boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from inspect import Parameter, signature
from threading import RLock, Thread
from typing import Any
from uuid import uuid4

from izfin_services.scan_page_state import tarama_sonuc_durumu_hazirla


_UNEXPECTED_SCAN_ERROR = "Tarama işlemi beklenmeyen bir hata nedeniyle tamamlanamadı."


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

    def get_for_owner(self, job_id: str, owner_uid: str) -> ScanJobSnapshot | None:
        with self._lock:
            record = self._records.get(str(job_id))
            if record is None:
                record = self._restore_terminal_record(str(job_id))
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
            record.result = {
                "sonuclar": presented["sonuclar"],
                "teknik_paneller": presented["teknik_paneller"],
                "sozlu_analizler": presented["sozlu_analizler"],
                "basarisiz_taramalar": presented["basarisiz_taramalar"],
                "boga_sayisi": presented["boga_sayisi"],
                "alim_firsati": presented["alim_firsati"],
            }
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
            record.status = "running"
            record.stage = stage
            if stage == "ticker":
                index = int(event.get("index") or 0)
                record.completed = min(max(index, 0), len(record.tickers))
            elif stage == "complete":
                record.completed = len(record.tickers)
            self._persist(record)

    def _persist(self, record: _ScanJobRecord) -> None:
        repository = self._job_repository
        if not getattr(repository, "available", False):
            return
        repository.upsert_job(
            record.job_id,
            {
                "job_id": record.job_id,
                "owner_uid": record.owner_uid,
                "tickers": list(record.tickers),
                "status": record.status,
                "stage": record.stage,
                "completed": record.completed,
                "result": record.result,
                "error": record.error,
            },
        )

    def _restore_terminal_record(self, job_id: str) -> _ScanJobRecord | None:
        repository = self._job_repository
        if not getattr(repository, "available", False):
            return None
        data = repository.get_job(job_id)
        if not data:
            return None
        status = str(data.get("status") or "failed")
        record = _ScanJobRecord(
            job_id=str(data.get("job_id") or job_id),
            owner_uid=str(data.get("owner_uid") or ""),
            tickers=tuple(str(item) for item in data.get("tickers") or ()),
            status=status,
            stage=str(data.get("stage") or status),
            completed=max(0, int(data.get("completed") or 0)),
            result=data.get("result") if isinstance(data.get("result"), dict) else None,
            error=str(data.get("error") or "") or None,
        )
        if record.status in {"queued", "running"}:
            record.status = "failed"
            record.stage = "interrupted"
            record.error = "Tarama işlemi uygulama yeniden başlatıldığı için tamamlanamadı."
            self._persist(record)
        self._records[record.job_id] = record
        return record
