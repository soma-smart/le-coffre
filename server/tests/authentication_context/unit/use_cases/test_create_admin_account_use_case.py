import pytest
from uuid import UUID

from authentication_context.application.use_cases import CreateAdminAccountUseCase
from authentication_context.application.commands import CreateAdminAccountCommand
from authentication_context.domain.entities import AdminAccount
from authentication_context.domain.exceptions import AdminAlreadyExistsException


@pytest.fixture
def use_case(admin_repository, password_hashing_gateway):
    return CreateAdminAccountUseCase(admin_repository, password_hashing_gateway)


def test_should_create_first_admin_account_and_return_admin_id(
    use_case: CreateAdminAccountUseCase, admin_repository
):
    admin_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password = "secure123!"
    display_name = "Admin User"

    command = CreateAdminAccountCommand(
        id=admin_id, email=email, password=password, display_name=display_name
    )

    result = use_case.execute(command)

    assert result == admin_id

    saved_admin = admin_repository.get_by_id(admin_id)
    assert saved_admin.id == admin_id
    assert saved_admin.email == email
    assert saved_admin.display_name == display_name
    assert saved_admin.password_hash == "hashed(secure123!)"


def test_should_raise_exception_when_admin_already_exists(
    use_case: CreateAdminAccountUseCase, admin_repository
):
    existing_admin_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    existing_admin = AdminAccount(
        id=existing_admin_id,
        email="existing@lecoffre.com",
        password_hash="hashed_password",
        display_name="Existing Admin",
    )
    admin_repository.save(existing_admin)

    new_admin_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    command = CreateAdminAccountCommand(
        id=new_admin_id,
        email="new@lecoffre.com",
        password="secure123!",
        display_name="New Admin",
    )

    with pytest.raises(AdminAlreadyExistsException):
        use_case.execute(command)

    assert admin_repository.get_by_id(new_admin_id) is None
    assert admin_repository.get_by_id(existing_admin_id) is not None


def test_should_hash_password_before_storing_admin(
    use_case: CreateAdminAccountUseCase, admin_repository
):
    admin_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    plain_password = "my_plain_password"
    display_name = "Admin User"

    command = CreateAdminAccountCommand(
        id=admin_id, email=email, password=plain_password, display_name=display_name
    )

    use_case.execute(command)

    saved_admin = admin_repository.get_by_id(admin_id)
    assert saved_admin.password_hash == "hashed(my_plain_password)"
    assert saved_admin.password_hash != plain_password
