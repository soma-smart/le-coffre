import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from main import _shutdown_vault_notification_executor


def _block_until_told(started: threading.Event, release: threading.Event) -> None:
    started.set()
    release.wait(timeout=5.0)


@pytest.mark.asyncio
async def test_given_a_stuck_in_flight_job_shutdown_should_return_within_the_bound(caplog):
    # Regression: an unreachable SMTP relay (blocked send, e.g. a 10s connection
    # timeout) must not make this shutdown step block far past that — it runs right
    # before the OTel flush, and a SIGKILL from an orchestrator's grace period would
    # otherwise lose exactly the spans/logs of the incident.
    executor = ThreadPoolExecutor(max_workers=1)
    started = threading.Event()
    release = threading.Event()
    in_flight = executor.submit(_block_until_told, started, release)
    started.wait(timeout=2.0)
    assert started.is_set(), "the in-flight job never started — test setup is broken"

    start = time.monotonic()
    await _shutdown_vault_notification_executor(executor, timeout_seconds=0.2)
    elapsed = time.monotonic() - start

    assert elapsed < 2.0, f"shutdown blocked for {elapsed}s despite a 0.2s bound"
    assert "did not drain" in caplog.text

    # Let the leaked worker thread finish so it doesn't outlive the test.
    release.set()
    in_flight.result(timeout=5.0)


@pytest.mark.asyncio
async def test_given_jobs_still_queued_past_the_bound_should_cancel_them():
    executor = ThreadPoolExecutor(max_workers=1)
    started = threading.Event()
    release = threading.Event()
    in_flight = executor.submit(_block_until_told, started, release)
    started.wait(timeout=2.0)
    queued = executor.submit(_block_until_told, threading.Event(), threading.Event())

    await _shutdown_vault_notification_executor(executor, timeout_seconds=0.2)

    assert queued.cancelled()

    release.set()
    in_flight.result(timeout=5.0)


@pytest.mark.asyncio
async def test_given_the_executor_drains_in_time_should_not_cancel_anything():
    executor = ThreadPoolExecutor(max_workers=1)
    done = executor.submit(lambda: "ok")

    await _shutdown_vault_notification_executor(executor, timeout_seconds=5.0)

    assert done.result() == "ok"
