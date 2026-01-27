
import pytest
from audit_logging_context.adapters.secondary.in_memory_audit_logger import InMemoryAuditLogger


@pytest.fixture
def audit_logger():
    """Create an InMemoryAuditLogger for testing without event publisher"""
    return InMemoryAuditLogger()
