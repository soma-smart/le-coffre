import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import _run_periodic_sweep, _shutdown_notification_executor


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
    await _shutdown_notification_executor(executor, timeout_seconds=0.2)
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

    await _shutdown_notification_executor(executor, timeout_seconds=0.2)

    assert queued.cancelled()

    release.set()
    in_flight.result(timeout=5.0)


@pytest.mark.asyncio
async def test_given_the_executor_drains_in_time_should_not_cancel_anything():
    executor = ThreadPoolExecutor(max_workers=1)
    done = executor.submit(lambda: "ok")

    await _shutdown_notification_executor(executor, timeout_seconds=5.0)

    assert done.result() == "ok"


# ── One-time link expiry sweep ────────────────────────────────────────


@pytest.mark.asyncio
async def test_given_a_periodic_sweep_should_run_the_job_repeatedly_until_cancelled():
    calls = []
    task = asyncio.create_task(_run_periodic_sweep(lambda: calls.append(1), interval_seconds=0.01))

    await asyncio.sleep(0.15)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(calls) >= 2
    count_at_cancel = len(calls)
    await asyncio.sleep(0.05)
    assert len(calls) == count_at_cancel


@pytest.mark.asyncio
async def test_given_a_pass_that_raises_the_sweep_should_log_it_and_keep_going(caplog):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database hiccup")

    task = asyncio.create_task(_run_periodic_sweep(flaky, interval_seconds=0.01))

    await asyncio.sleep(0.15)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(calls) >= 2
    assert "expiry sweep failed" in caplog.text
    assert "database hiccup" in caplog.text


def test_given_the_app_lifespan_the_sweep_should_start_only_after_migrations_and_stop_at_shutdown(
    monkeypatch, tmp_path, env_vars
):
    import main

    migrations_may_finish = threading.Event()
    sweeps = []

    def slow_migrations():
        migrations_may_finish.wait(timeout=10.0)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'lifespan.db'}")
    monkeypatch.setattr(main, "run_migrations", slow_migrations)
    monkeypatch.setattr(main, "_record_vault_locked_on_startup", lambda *_: None)
    monkeypatch.setattr(main, "_publish_expired_one_time_links", lambda *_: sweeps.append(time.monotonic()))
    monkeypatch.setattr(main, "get_one_time_link_expiry_sweep_interval_seconds", lambda: 0.02)

    with TestClient(main.app) as _:
        time.sleep(0.3)
        assert sweeps == [], "the sweep ran before the migrations had finished"
        assert main.app.state.ready is False

        migrations_may_finish.set()
        deadline = time.monotonic() + 5.0
        while not sweeps and time.monotonic() < deadline:
            time.sleep(0.02)
        assert sweeps, "the sweep never started once the migrations were done"
        assert main.app.state.ready is True
        sweep_task = main.app.state.expiry_sweep_task

    assert sweep_task.done()
    count_after_shutdown = len(sweeps)
    time.sleep(0.2)
    assert len(sweeps) == count_after_shutdown


def test_given_failed_migrations_the_sweep_should_never_run(monkeypatch, tmp_path, env_vars):
    import main

    sweeps = []

    def broken_migrations():
        raise RuntimeError("migration failed")

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'lifespan_failed.db'}")
    monkeypatch.setattr(main, "run_migrations", broken_migrations)
    monkeypatch.setattr(main, "_publish_expired_one_time_links", lambda *_: sweeps.append(1))
    monkeypatch.setattr(main, "get_one_time_link_expiry_sweep_interval_seconds", lambda: 0.02)

    with TestClient(main.app) as _:
        time.sleep(0.3)
        assert main.app.state.migration_failed is True
        sweep_task = main.app.state.expiry_sweep_task

    assert sweep_task.done()
    assert sweeps == []


@pytest.mark.parametrize("value", ["0", "-5", "abc", ""])
def test_given_an_invalid_sweep_interval_the_startup_should_fail_instead_of_the_sweep_task(
    monkeypatch, tmp_path, env_vars, value
):
    import main

    migrations = []

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'lifespan_invalid_interval.db'}")
    monkeypatch.setenv("ONE_TIME_LINK_EXPIRY_SWEEP_INTERVAL_SECONDS", value)
    monkeypatch.setattr(main, "run_migrations", lambda: migrations.append(1))

    with pytest.raises(ValueError):
        with TestClient(main.app) as _:
            pass

    assert migrations == [], "the app started despite an invalid sweep interval"


def test_given_a_sweep_task_that_died_with_an_error_shutdown_should_still_drain_the_executor(
    monkeypatch, tmp_path, env_vars, caplog
):
    import main

    drained = []
    original_shutdown = main._shutdown_notification_executor

    async def dying_sweep(*_):
        raise RuntimeError("sweep exploded")

    async def recording_shutdown(*args):
        drained.append(1)
        await original_shutdown(*args)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'lifespan_dead_sweep.db'}")
    monkeypatch.setattr(main, "run_migrations", lambda: None)
    monkeypatch.setattr(main, "_record_vault_locked_on_startup", lambda *_: None)
    monkeypatch.setattr(main, "_run_periodic_sweep", dying_sweep)
    monkeypatch.setattr(main, "_shutdown_notification_executor", recording_shutdown)

    with TestClient(main.app) as _:
        deadline = time.monotonic() + 5.0
        while not main.app.state.expiry_sweep_task.done() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert main.app.state.expiry_sweep_task.done(), "test setup is broken: the sweep task is still running"

    assert drained == [1]
    assert "sweep task ended with an error" in caplog.text
    assert "sweep exploded" in caplog.text
