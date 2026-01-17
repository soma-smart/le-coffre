import pytest
from unittest.mock import patch
from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
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
    GroupNotFoundError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.services.password_complexity_service import (
    PasswordComplexityService,
)


STRONG_PASSWORD = "StrongP@ssw0rd123"


@pytest.fixture
def use_case(
    password_repository,
    encryption_service,
    password_permissions_repository,
    group_access_gateway,
):
    return CreatePasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
    )


def test_should_create_password_when_user_owns_group(
    use_case: CreatePasswordUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway: GroupAccessGateway,
):
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    name = "My Password"
    decrypted_password = STRONG_PASSWORD

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=password_id,
        name=name,
        decrypted_password=decrypted_password,
    )

    result_id = use_case.execute(command)

    assert result_id == password_id
    saved_password = password_repository.get_by_id(password_id)
    assert saved_password is not None
    assert saved_password.name == name


def test_should_raise_when_user_is_not_owner_of_group(
    use_case: CreatePasswordUseCase,
    group_access_gateway: GroupAccessGateway,
):
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    other_user_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e8")

    group_access_gateway.set_group_owner(group_id, other_user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=password_id,
        name="My Password",
        decrypted_password=STRONG_PASSWORD,
    )

    with pytest.raises(UserNotOwnerOfGroupError) as exc_info:
        use_case.execute(command)

    assert str(user_id) in str(exc_info.value)
    assert str(group_id) in str(exc_info.value)


def test_should_raise_when_group_does_not_exist(
    use_case: CreatePasswordUseCase,
):
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=password_id,
        name="My Password",
        decrypted_password=STRONG_PASSWORD,
    )

    with pytest.raises(GroupNotFoundError) as exc_info:
        use_case.execute(command)

    assert str(group_id) in str(exc_info.value)


def test_should_set_group_as_owner_of_password(
    use_case: CreatePasswordUseCase,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway: GroupAccessGateway,
):
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=password_id,
        name="My Password",
        decrypted_password=STRONG_PASSWORD,
    )

    use_case.execute(command)

    assert password_permissions_repository.is_owner(group_id, password_id)


def test_should_create_password_with_uuid_and_store_encrypted(
    use_case: CreatePasswordUseCase,
    password_repository: PasswordRepository,
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    name = "name"
    decrypted_password = STRONG_PASSWORD
    expected_encrypted = "encrypted(" + decrypted_password + ")"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name=name,
        decrypted_password=decrypted_password,
    )

    password_id = use_case.execute(command)

    assert password_id == uuid

    saved_password = password_repository.get_by_id(password_id)
    assert saved_password.id == uuid
    assert saved_password.name == name
    assert saved_password.encrypted_value == expected_encrypted


def test_should_create_password_in_folder_with_encrypted_value(
    use_case: CreatePasswordUseCase,
    password_repository: PasswordRepository,
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    folder = "Work"
    name = "Slack"
    decrypted_password = STRONG_PASSWORD
    expected_encrypted = "encrypted(" + decrypted_password + ")"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
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
    use_case: CreatePasswordUseCase,
    password_repository: PasswordRepository,
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    name = "Slack"
    decrypted_password = STRONG_PASSWORD

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
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
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    name = "name"
    decrypted_password = STRONG_PASSWORD

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name=name,
        decrypted_password=decrypted_password,
    )

    use_case.execute(command)

    assert password_permissions_repository.is_owner(group_id, uuid)


def test_should_reject_password_with_multiple_complexity_violations(
    use_case: CreatePasswordUseCase,
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    weak_password = "weak"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name="name",
        decrypted_password=weak_password,
    )

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
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    password_missing_uppercase = "strongp@ssw0rd123"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name="name",
        decrypted_password=password_missing_uppercase,
    )

    with pytest.raises(PasswordMissingUppercaseError):
        use_case.execute(command)


def test_should_validate_password_complexity_before_creation(
    use_case: CreatePasswordUseCase,
    password_repository: PasswordRepository,
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    strong_password = "StrongP@ssw0rd123"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name="name",
        decrypted_password=strong_password,
    )

    password_id = use_case.execute(command)

    assert password_id == uuid
    saved_password = password_repository.get_by_id(password_id)
    assert saved_password is not None


def test_should_reject_password_with_forbidden_pattern(
    use_case: CreatePasswordUseCase,
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    password_with_forbidden = "MyStrongPass123456!"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name="name",
        decrypted_password=password_with_forbidden,
    )

    with pytest.raises(PasswordContainsForbiddenPatternError) as exc_info:
        use_case.execute(command)

    assert exc_info.value.forbidden_pattern == "123456"


def test_should_reject_password_too_short(
    use_case: CreatePasswordUseCase,
    group_access_gateway: GroupAccessGateway,
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    short_password = "Short1!"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name="name",
        decrypted_password=short_password,
    )

    with pytest.raises(PasswordTooShortError) as exc_info:
        use_case.execute(command)

    assert exc_info.value.current_length == 7
    assert exc_info.value.min_length == 12


@patch.object(PasswordComplexityService, "validate")
def test_should_call_password_complexity_service_validate(
    mock_validate,
    use_case: CreatePasswordUseCase,
    group_access_gateway: GroupAccessGateway,
):
    mock_validate.return_value = None

    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    password = "TestPassword123!"

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=uuid,
        name="name",
        decrypted_password=password,
    )

    use_case.execute(command)

    mock_validate.assert_called_once_with(password)
