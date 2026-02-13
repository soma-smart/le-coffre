import logging
import pytest
from main import _HealthCheckFilter


@pytest.fixture
def filter_instance():
    return _HealthCheckFilter()


def make_record(message: str) -> logging.LogRecord:
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    return record


def test_health_200_is_filtered(filter_instance):
    """Successful health check probes must not appear in logs."""
    record = make_record('100.64.7.58:57990 - "GET /api/health HTTP/1.1" 200 OK')
    assert filter_instance.filter(record) is False


def test_health_503_is_not_filtered(filter_instance):
    """Failed health checks (DB down) must remain visible in logs."""
    record = make_record(
        '100.64.7.58:57990 - "GET /api/health HTTP/1.1" 503 Service Unavailable'
    )
    assert filter_instance.filter(record) is True


def test_other_routes_are_not_filtered(filter_instance):
    """Business endpoint logs must not be affected by the filter."""
    record = make_record('100.64.7.208:35250 - "GET /api/passwords/list HTTP/1.1" 200 OK')
    assert filter_instance.filter(record) is True
