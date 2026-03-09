from fastapi import Depends
from sqlmodel import Session
from starlette.requests import Request

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_user_info_api,
)
from identity_access_management_context.adapters.primary.private_api import (
    UserInfoApi,
)
from identity_access_management_context.adapters.secondary.group_access_gateway_adapter import (
    GroupAccessGatewayAdapter,
)
from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupMemberRepository,
    SqlGroupRepository,
)
from password_management_context.adapters.secondary import (
    SqlPasswordEventRepository,
    SqlPasswordPermissionsRepository,
    SqlPasswordRepository,
)
from password_management_context.adapters.secondary.gateways.iam_user_info_gateway import (
    IamUserInfoGateway,
)
from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordEncryptionGateway,
    PasswordEventRepository,
    PasswordRepository,
    UserInfoGateway,
)
from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from password_management_context.application.use_cases import (
    CreatePasswordUseCase,
    DeletePasswordUseCase,
    GetPasswordUseCase,
    ListAccessUseCase,
    ListPasswordEventsUseCase,
    ListPasswordsUseCase,
    ShareAccessUseCase,
    UnshareAccessUseCase,
    UpdatePasswordUseCase,
)
from shared_kernel.adapters.primary.dependencies import get_session
from shared_kernel.application.gateways import DomainEventPublisher


def get_password_repository(
    session: Session = Depends(get_session),  # noqa: B008
) -> PasswordRepository:
    return SqlPasswordRepository(session)


def get_password_encryption_gateway(request: Request) -> PasswordEncryptionGateway:
    return request.app.state.password_encryption_gateway


def get_password_permissions_repository(
    session: Session = Depends(get_session),  # noqa: B008
) -> PasswordPermissionsRepository:
    return SqlPasswordPermissionsRepository(session)


def get_password_event_repository(
    session: Session = Depends(get_session),  # noqa: B008
) -> PasswordEventRepository:
    return SqlPasswordEventRepository(session)


def get_group_access_gateway(
    session: Session = Depends(get_session),  # noqa: B008
) -> GroupAccessGateway:
    group_repository = SqlGroupRepository(session)
    group_member_repository = SqlGroupMemberRepository(session)
    return GroupAccessGatewayAdapter(group_repository, group_member_repository)


def get_user_info_gateway(
    user_info_api: UserInfoApi = Depends(get_user_info_api),  # noqa: B008
) -> UserInfoGateway:
    return IamUserInfoGateway(user_info_api)


def get_event_publisher(request: Request) -> DomainEventPublisher:
    return request.app.state.domain_event_publisher


def get_create_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_encryption_gateway: PasswordEncryptionGateway = Depends(  # noqa: B008
        get_password_encryption_gateway
    ),
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
):
    return CreatePasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_get_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_encryption_gateway: PasswordEncryptionGateway = Depends(  # noqa: B008
        get_password_encryption_gateway
    ),
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
):
    return GetPasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_update_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_encryption_gateway: PasswordEncryptionGateway = Depends(  # noqa: B008
        get_password_encryption_gateway
    ),
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
):
    return UpdatePasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_list_passwords_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
):
    return ListPasswordsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
    )


def get_delete_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
):
    return DeletePasswordUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_share_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
):
    return ShareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_unshare_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
):
    return UnshareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_list_resource_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
):
    return ListAccessUseCase(password_repository, password_permissions_repository, group_access_gateway)


def get_list_password_events_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),  # noqa: B008
    password_permissions_repository: PasswordPermissionsRepository = Depends(  # noqa: B008
        get_password_permissions_repository
    ),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),  # noqa: B008
    password_event_repository: PasswordEventRepository = Depends(  # noqa: B008
        get_password_event_repository
    ),
    user_info_gateway: UserInfoGateway = Depends(get_user_info_gateway),  # noqa: B008
):
    return ListPasswordEventsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
        user_info_gateway,
    )
