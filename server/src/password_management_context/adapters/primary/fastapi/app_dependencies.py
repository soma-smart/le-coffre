from fastapi import Depends
from starlette.requests import Request

from password_management_context.application.use_cases import (
    CreatePasswordUseCase,
    GetPasswordUseCase,
    UpdatePasswordUseCase,
    ListPasswordsUseCase,
    DeletePasswordUseCase,
)
from password_management_context.application.gateways import PasswordRepository
from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from shared_kernel.encryption import EncryptionService
from rights_access_context.application.use_cases import (
    ShareAccessUseCase,
    UnshareAccessUseCase,
)
from rights_access_context.application.gateways import (
    RightsRepository,
    UserManagementGateway,
)
from rights_access_context.adapters.secondary import UserRepositoryAdapter
from identity_access_management_context.application.gateways import UserRepository


def get_password_repository(request: Request) -> PasswordRepository:
    return request.app.state.password_repository


def get_encryption_service(request: Request) -> EncryptionService:
    return request.app.state.encryption_service


def get_password_permissions_repository(
    request: Request,
) -> PasswordPermissionsRepository:
    return request.app.state.password_permissions_repository


def get_create_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    encryption_service: EncryptionService = Depends(get_encryption_service),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
):
    return CreatePasswordUseCase(
        password_repository, encryption_service, password_permissions_repository
    )


def get_get_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    encryption_service: EncryptionService = Depends(get_encryption_service),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
):
    return GetPasswordUseCase(
        password_repository, encryption_service, password_permissions_repository
    )


def get_update_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    encryption_service: EncryptionService = Depends(get_encryption_service),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
):
    return UpdatePasswordUseCase(
        password_repository, encryption_service, password_permissions_repository
    )


def get_list_passwords_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
):
    return ListPasswordsUseCase(password_repository, password_permissions_repository)


def get_delete_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
):
    return DeletePasswordUseCase(password_repository, password_permissions_repository)


def get_rights_repository(request: Request) -> RightsRepository:
    return request.app.state.rights_repository


def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repository


def get_user_management_gateway(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserManagementGateway:
    return UserRepositoryAdapter(user_repository)


def get_share_access_usecase(
    rights_repository: RightsRepository = Depends(get_rights_repository),
    user_management_gateway: UserManagementGateway = Depends(
        get_user_management_gateway
    ),
):
    return ShareAccessUseCase(rights_repository, user_management_gateway)


def get_unshare_access_usecase(
    rights_repository: RightsRepository = Depends(get_rights_repository),
):
    return UnshareAccessUseCase(rights_repository)
