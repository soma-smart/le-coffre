from fastapi import Depends
from starlette.requests import Request
from sqlmodel import Session
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupRepository,
    SqlGroupMemberRepository,
    SqlUserRepository,
)
from identity_access_management_context.adapters.secondary.group_access_gateway_adapter import (
    GroupAccessGatewayAdapter,
)
from password_management_context.application.gateways import (
    PasswordRepository,
    GroupAccessGateway,
    PasswordEncryptionGateway,
    PasswordEventRepository,
)
from password_management_context.application.services import (
    PasswordEventStorageService,
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
    ListPasswordEventsUseCase,
)
from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from password_management_context.adapters.secondary import (
    SqlPasswordRepository,
    SqlPasswordPermissionsRepository,
    SqlPasswordEventRepository,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.adapters.primary.dependencies import get_session


def get_password_repository(
    session: Session = Depends(get_session),
) -> PasswordRepository:
    return SqlPasswordRepository(session)


def get_password_encryption_gateway(request: Request) -> PasswordEncryptionGateway:
    return request.app.state.password_encryption_gateway


def get_password_permissions_repository(
    session: Session = Depends(get_session),
) -> PasswordPermissionsRepository:
    return SqlPasswordPermissionsRepository(session)


def get_password_event_repository(
    session: Session = Depends(get_session),
) -> PasswordEventRepository:
    return SqlPasswordEventRepository(session)


def get_password_event_storage_service(
    password_event_repository: PasswordEventRepository = Depends(
        get_password_event_repository
    ),
) -> PasswordEventStorageService:
    return PasswordEventStorageService(password_event_repository)


def get_group_access_gateway(
    session: Session = Depends(get_session),
) -> GroupAccessGateway:
    group_repository = SqlGroupRepository(session)
    group_member_repository = SqlGroupMemberRepository(session)
    return GroupAccessGatewayAdapter(group_repository, group_member_repository)


def get_event_publisher(request: Request) -> DomainEventPublisher:
    return request.app.state.domain_event_publisher


def get_create_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_encryption_gateway: PasswordEncryptionGateway = Depends(
        get_password_encryption_gateway
    ),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    event_storage_service: PasswordEventStorageService = Depends(
        get_password_event_storage_service
    ),
):
    return CreatePasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        event_storage_service,
    )


def get_get_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_encryption_gateway: PasswordEncryptionGateway = Depends(
        get_password_encryption_gateway
    ),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    event_storage_service: PasswordEventStorageService = Depends(
        get_password_event_storage_service
    ),
):
    return GetPasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        event_storage_service,
    )


def get_update_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_encryption_gateway: PasswordEncryptionGateway = Depends(
        get_password_encryption_gateway
    ),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    event_storage_service: PasswordEventStorageService = Depends(
        get_password_event_storage_service
    ),
):
    return UpdatePasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        event_storage_service,
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
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    event_storage_service: PasswordEventStorageService = Depends(
        get_password_event_storage_service
    ),
):
    return DeletePasswordUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        event_storage_service,
    )


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return SqlUserRepository(session)


def get_share_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    event_storage_service: PasswordEventStorageService = Depends(
        get_password_event_storage_service
    ),
):
    return ShareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        event_storage_service,
    )


def get_unshare_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    event_storage_service: PasswordEventStorageService = Depends(
        get_password_event_storage_service
    ),
):
    return UnshareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        event_storage_service,
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


def get_list_password_events_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    password_event_repository: PasswordEventRepository = Depends(
        get_password_event_repository
    ),
):
    return ListPasswordEventsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
    )
