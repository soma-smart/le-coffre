import asyncio
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from tests.shared_kernel.fakes import FakeTimeGateway
from vault_management_context.adapters.primary.scheduled import ExpiredShareLinkPurgeJob
from vault_management_context.adapters.secondary import SqlShareLinkRepository
from vault_management_context.domain.entities import ShareLink

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def _link(index: int, issued_at: datetime) -> ShareLink:
    return ShareLink.create(
        setup_id="setup-1",
        share_index=index,
        lookup_hash=hashlib.sha256(f"token-{index}".encode()).hexdigest(),
        ack_hash=hashlib.sha256(f"ack-{index}".encode()).hexdigest(),
        sealed_share=f"sealed-{index}",
        now=issued_at,
    )


def test_run_once_deletes_expired_links_and_keeps_live_ones(database_engine):
    session_maker = sessionmaker(bind=database_engine, class_=Session, expire_on_commit=False)
    with session_maker() as session:
        SqlShareLinkRepository(session).replace_all(
            [_link(1, NOW - timedelta(hours=49)), _link(2, NOW - timedelta(hours=47))]
        )

    ExpiredShareLinkPurgeJob(session_maker, FakeTimeGateway(NOW)).run_once()

    with session_maker() as session:
        repository = SqlShareLinkRepository(session)
        assert repository.get_by_lookup_hash(_link(1, NOW).lookup_hash) is None
        assert repository.get_by_lookup_hash(_link(2, NOW).lookup_hash) is not None


class _RecordingJob(ExpiredShareLinkPurgeJob):
    """Counts runs instead of touching a database, failing the first ones on demand."""

    def __init__(self, failures: int = 0):
        super().__init__(
            session_maker=None,  # type: ignore[arg-type]
            time_gateway=FakeTimeGateway(NOW),
            interval_seconds=0.001,
            not_ready_retry_seconds=0.001,
        )
        self.runs = 0
        self._failures = failures

    def run_once(self) -> None:
        self.runs += 1
        if self.runs <= self._failures:
            raise RuntimeError("database unavailable")


async def _run_until(job: _RecordingJob, is_ready, done) -> None:
    task = asyncio.create_task(job.run_forever(is_ready))
    try:
        for _ in range(1000):
            if done():
                return
            await asyncio.sleep(0.001)
        pytest.fail("the job did not get there in time")
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_run_forever_waits_for_the_migrations_before_purging():
    job = _RecordingJob()
    checks = 0

    def is_ready() -> bool:
        nonlocal checks
        checks += 1
        assert job.runs == 0, "purged before the schema was ready"
        return checks > 3

    await _run_until(job, is_ready, done=lambda: job.runs >= 1)


@pytest.mark.asyncio
async def test_run_forever_keeps_purging_after_a_failed_run(caplog):
    job = _RecordingJob(failures=1)

    await _run_until(job, is_ready=lambda: True, done=lambda: job.runs >= 2)

    assert "Purging expired share links failed" in caplog.text
