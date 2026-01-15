import pytest
from unittest.mock import patch
from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.application.commands import CreatePasswordCommand
from password_management_context.application.use_cases import CreatePasswordUseCase

from password_management_context.domain.exceptions import (
    PasswordMultipleComplexityError,
    PasswordTooShortError,
    PasswordMissingUppercaseError,
    PasswordMissingDigitError,
    PasswordMissingSpecialCharError,
    PasswordContainsForbiddenPatternError,
)
from password_management_context.domain.services.password_complexity_service import (
    PasswordComplexityService,
)


STRONG_PASSWORD = "StrongP@ssw0rd123"


@pytest.fixture
def use_case(password_repository, encryption_service, password_permissions_repository):
    return CreatePasswordUseCase(
        password_repository, encryption_service, password_permissions_repository
    )


def test_should_create_password_with_uuid_and_store_encrypted(
    use_case: CreatePasswordUseCase, password_repository: PasswordRepository
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    name = "name"
    decrypted_password = STRONG_PASSWORD
    expected_encrypted = "encrypted(" + decrypted_password + ")"

    command = CreatePasswordCommand(
        user_id=user_id, id=uuid, name=name, decrypted_password=decrypted_password
    )

    password_id = use_case.execute(command)

    assert password_id == uuid

    saved_password = password_repository.get_by_id(password_id)
    assert saved_password.id == uuid
    assert saved_password.name == name
    assert saved_password.encrypted_value == expected_encrypted


def test_should_create_password_in_folder_with_encrypted_value(
    use_case: CreatePasswordUseCase, password_repository: PasswordRepository
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    folder = "Work"
    name = "Slack"
    decrypted_password = STRONG_PASSWORD
    expected_encrypted = "encrypted(" + decrypted_password + ")"

    command = CreatePasswordCommand(
        user_id=user_id,
        id=uuid,
        name=name,
        decrypted_password=decrypted_password,
        folder=folder,
    )

    password_id = use_case.execute(command)

    assert password_id == uuid
    saved_password = password_repository.get_by_id(password_id)
    assert saved_password.name == name
    assert saved_password.folder == folder
    assert saved_password.encrypted_value == expected_encrypted


def test_should_create_password_in_default_folder_when_not_given(
    use_case: CreatePasswordUseCase, password_repository: PasswordRepository
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    name = "Slack"
    decrypted_password = STRONG_PASSWORD

    command = CreatePasswordCommand(
        user_id=user_id,
        id=uuid,
        name=name,
        decrypted_password=decrypted_password,
    )

    password_id = use_case.execute(command)

    assert password_id == uuid
    saved_password = password_repository.get_by_id(password_id)
    assert saved_password.folder == "default"


def test_should_set_user_as_owner_when_creating_password(
    use_case: CreatePasswordUseCase,
    password_permissions_repository: PasswordPermissionsRepository,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    name = "name"
    decrypted_password = STRONG_PASSWORD

    command = CreatePasswordCommand(
        user_id=user_id, id=uuid, name=name, decrypted_password=decrypted_password
    )

    use_case.execute(command)

    assert password_permissions_repository.is_owner(user_id, uuid)


def test_should_reject_password_with_multiple_complexity_violations(
    use_case: CreatePasswordUseCase,
):
    # ARRANGE
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    weak_password = "weak"

    command = CreatePasswordCommand(
        user_id=user_id, id=uuid, name="name", decrypted_password=weak_password
    )

    # ACT & ASSERT
    with pytest.raises(PasswordMultipleComplexityError) as exc_info:
        use_case.execute(command)

    violations = exc_info.value.violations
    violation_types = [type(v) for v in violations]

    assert PasswordTooShortError in violation_types
    assert PasswordMissingUppercaseError in violation_types
    assert PasswordMissingDigitError in violation_types
    assert PasswordMissingSpecialCharError in violation_types


def test_should_reject_password_with_single_complexity_violation(
    use_case: CreatePasswordUseCase,
):
    # ARRANGE
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password_missing_uppercase = "strongp@ssw0rd123"

    command = CreatePasswordCommand(
        user_id=user_id,
        id=uuid,
        name="name",
        decrypted_password=password_missing_uppercase,
    )

    # ACT & ASSERT
    with pytest.raises(PasswordMissingUppercaseError):
        use_case.execute(command)


def test_should_validate_password_complexity_before_creation(
    use_case: CreatePasswordUseCase,
    password_repository: PasswordRepository,
):
    # ARRANGE
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    strong_password = "StrongP@ssw0rd123"

    command = CreatePasswordCommand(
        user_id=user_id, id=uuid, name="name", decrypted_password=strong_password
    )

    # ACT
    password_id = use_case.execute(command)

    # ASSERT
    assert password_id == uuid
    saved_password = password_repository.get_by_id(password_id)
    assert saved_password is not None


def test_should_reject_password_with_forbidden_pattern(
    use_case: CreatePasswordUseCase,
):
    # ARRANGE
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password_with_forbidden = "MyStrongPass123456!"

    command = CreatePasswordCommand(
        user_id=user_id,
        id=uuid,
        name="name",
        decrypted_password=password_with_forbidden,
    )

    # ACT & ASSERT
    with pytest.raises(PasswordContainsForbiddenPatternError) as exc_info:
        use_case.execute(command)

    assert exc_info.value.forbidden_pattern == "123456"


def test_should_reject_password_too_short(
    use_case: CreatePasswordUseCase,
):
    # ARRANGE
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    short_password = "Short1!"

    command = CreatePasswordCommand(
        user_id=user_id, id=uuid, name="name", decrypted_password=short_password
    )

    # ACT & ASSERT
    with pytest.raises(PasswordTooShortError) as exc_info:
        use_case.execute(command)

    assert exc_info.value.current_length == 7
    assert exc_info.value.min_length == 12


@patch.object(PasswordComplexityService, "validate")
def test_should_call_password_complexity_service_validate(
    mock_validate,
    use_case: CreatePasswordUseCase,
):
    # ARRANGE
    mock_validate.return_value = None

    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password = "TestPassword123!"

    command = CreatePasswordCommand(
        user_id=user_id, id=uuid, name="name", decrypted_password=password
    )

    # ACT
    use_case.execute(command)

    # ASSERT
    mock_validate.assert_called_once_with(password)
