from uuid import uuid4

import pytest

from identity_access_management_context.domain.entities import SsoUser
from identity_access_management_context.domain.exceptions import (
    SsoUserAlreadyExistsException,
)


def test_save_sso_user_and_get_by_internal_user_id(sql_sso_user_repository):
    sso_user = SsoUser(
        internal_user_id=uuid4(),
        email="test@soma-smart.com",
        display_name="Test User",
        sso_user_id="sso123",
        sso_provider="google",
    )
    sql_sso_user_repository.create(sso_user)
    retrieved_user = sql_sso_user_repository.get_by_user_id(sso_user.internal_user_id)
    assert retrieved_user is not None
    assert retrieved_user.email == sso_user.email
    assert retrieved_user.display_name == sso_user.display_name
    assert retrieved_user.sso_user_id == sso_user.sso_user_id
    assert retrieved_user.sso_provider == sso_user.sso_provider


def test_sso_user_already_exists(sql_sso_user_repository):
    sso_user = SsoUser(
        internal_user_id=uuid4(),
        email="test@soma-smart.com",
        display_name="Test User",
        sso_user_id="sso123",
        sso_provider="google",
    )
    sql_sso_user_repository.create(sso_user)
    with pytest.raises(SsoUserAlreadyExistsException):
        sql_sso_user_repository.create(sso_user)


def test_get_nonexistent_sso_user(sql_sso_user_repository):
    non_existent_user_id = str(uuid4())
    result = sql_sso_user_repository.get_by_sso_user_id(non_existent_user_id)
    assert result is None


def test_get_user_by_sso_user_id(sql_sso_user_repository):
    sso_user = SsoUser(
        internal_user_id=uuid4(),
        email="test@soma-smart.com",
        display_name="Test User",
        sso_user_id="sso123",
        sso_provider="google",
    )
    sql_sso_user_repository.create(sso_user)
    retrieved_user = sql_sso_user_repository.get_by_sso_user_id("sso123", "google")
    assert retrieved_user is not None
    assert retrieved_user.email == sso_user.email
    assert retrieved_user.display_name == sso_user.display_name
    assert retrieved_user.sso_user_id == sso_user.sso_user_id
    assert retrieved_user.sso_provider == sso_user.sso_provider


def test_get_user_by_internal_user_id(sql_sso_user_repository):
    iud = uuid4()
    sso_user = SsoUser(
        internal_user_id=iud,
        email="test@soma-smart.com",
        display_name="Test User",
        sso_user_id="sso123",
        sso_provider="google",
    )
    sql_sso_user_repository.create(sso_user)
    retrieved_user = sql_sso_user_repository.get_by_user_id(iud)
    assert retrieved_user is not None
    assert retrieved_user.email == sso_user.email
    assert retrieved_user.display_name == sso_user.display_name
    assert retrieved_user.sso_user_id == sso_user.sso_user_id
    assert retrieved_user.sso_provider == sso_user.sso_provider
