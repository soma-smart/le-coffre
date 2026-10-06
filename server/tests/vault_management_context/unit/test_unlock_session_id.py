import pytest

from vault_management_context.domain.exceptions import InvalidUnlockSessionIdError
from vault_management_context.domain.value_objects import UnlockSessionId


@pytest.mark.parametrize("value", ["ZOJRGBIZK4XQ7M2P", "a" * 64, "abc_DEF-123_ghi-4"])
def test_should_accept_well_formed_ids(value):
    assert UnlockSessionId(value).value == value


@pytest.mark.parametrize("value", ["", "SHORT", "a" * 15, "a" * 65, "ZOJRGBIZK4XQ7M2P!", "ZOJRGBIZ K4XQ7M2P"])
def test_should_reject_malformed_ids(value):
    with pytest.raises(InvalidUnlockSessionIdError):
        UnlockSessionId(value)
