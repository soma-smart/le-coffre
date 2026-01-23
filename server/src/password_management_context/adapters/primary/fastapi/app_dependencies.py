from fastapi import Depends
from starlette.requests import Request
from identity_access_management_context.application.gateways import UserRepository
from password_management_context.application.gateways import (
    PasswordRepository,
    GroupAccessGateway,
)
from password_management_context.application.use_cases import (
    GetPasswordUseCase,
    UpdatePasswordUseCase,
    CreatePasswordUseCase,
    DeletePasswordUseCase,
    ShareAccessUseCase,
    UnshareAccessUseCase,
    ListPasswordsUseCase,
    ListAccessUseCase,
)
from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from shared_kernel.encryption import EncryptionService
from shared_kernel.pubsub.gateway.event_publisher_gateway import DomainEventPublisher


def get_password_repository(request: Request) -> PasswordRepository:
    return request.app.state.password_repository


def get_encryption_service(request: Request) -> EncryptionService:
    return request.app.state.encryption_service


def get_password_permissions_repository(
    request: Request,
) -> PasswordPermissionsRepository:
    return request.app.state.password_permissions_repository


def get_group_access_gateway(request: Request) -> GroupAccessGateway:
    return request.app.state.group_access_gateway


def get_event_publisher(request: Request) -> DomainEventPublisher:
    return request.app.state.domain_event_publisher


def get_create_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    encryption_service: EncryptionService = Depends(get_encryption_service),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
):
    return CreatePasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
    )


def get_get_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    encryption_service: EncryptionService = Depends(get_encryption_service),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return GetPasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
    )


def get_update_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    encryption_service: EncryptionService = Depends(get_encryption_service),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return UpdatePasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
    )


def get_list_passwords_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return ListPasswordsUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


def get_delete_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return DeletePasswordUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repository


def get_share_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return ShareAccessUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


def get_unshare_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return UnshareAccessUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


def get_list_resource_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return ListAccessUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )
