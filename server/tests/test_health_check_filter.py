import logging
import pytest
from main import _NoiseFilter


@pytest.fixture
def filter_instance():
    return _NoiseFilter()


def make_uvicorn_record(client: str, method: str, path: str, status: int) -> logging.LogRecord:
    """Build a log record matching uvicorn's actual access log format."""
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=(client, method, path, "1.1", status),
        exc_info=None,
    )
    return record


def test_health_200_is_filtered(filter_instance):
    """Successful health check probes must not appear in logs."""
    record = make_uvicorn_record("100.64.7.58:57990", "GET", "/api/health", 200)
    assert filter_instance.filter(record) is False


def test_health_503_is_not_filtered(filter_instance):
    """Failed health checks (DB down) must remain visible in logs."""
    record = make_uvicorn_record("100.64.7.58:57990", "GET", "/api/health", 503)
    assert filter_instance.filter(record) is True


def test_metrics_200_is_filtered(filter_instance):
    """Successful Prometheus scrapes must not appear in logs."""
    record = make_uvicorn_record("10.32.7.62:12345", "GET", "/api/metrics", 200)
    assert filter_instance.filter(record) is False


def test_metrics_503_is_not_filtered(filter_instance):
    """Failed Prometheus scrapes must remain visible in logs."""
    record = make_uvicorn_record("10.32.7.62:12345", "GET", "/api/metrics", 503)
    assert filter_instance.filter(record) is True


def test_other_routes_are_not_filtered(filter_instance):
    """Business endpoint logs must not be affected by the filter."""
    record = make_uvicorn_record("100.64.7.208:35250", "GET", "/api/passwords/list", 200)
    assert filter_instance.filter(record) is True
