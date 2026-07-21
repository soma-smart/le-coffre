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
    PrivateApiPasswordVaultAccessGateway,
    SqlOneTimeLinkRepository,
    SqlPasswordEventRepository,
    SqlPasswordPermissionsRepository,
    SqlPasswordRepository,
)
from password_management_context.adapters.secondary.gateways.iam_user_info_gateway import (
    IamUserInfoGateway,
)
from password_management_context.application.gateways import (
    GroupAccessGateway,
    OneTimeLinkRepository,
    PasswordEncryptionGateway,
    PasswordEventRepository,
    PasswordRepository,
    PasswordVaultAccessGateway,
    UserInfoGateway,
)
from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from password_management_context.application.services import (
    OneTimeLinkAuditAssembler,
    PasswordOwnershipService,
)
from password_management_context.application.use_cases import (
    ConsumeOneTimeLinkUseCase,
    CreateOneTimeLinkUseCase,
    CreatePasswordUseCase,
    DeletePasswordUseCase,
    GetPasswordStatisticForAdminUseCase,
    GetPasswordUseCase,
    ListAccessUseCase,
    ListMyOneTimeLinksUseCase,
    ListOneTimeLinksForAdminUseCase,
    ListOneTimeLinksUseCase,
    ListPasswordEventsByActorUseCase,
    ListPasswordEventsUseCase,
    ListPasswordsUseCase,
    RevokeAllOneTimeLinksForUserUseCase,
    RevokeOneTimeLinkForAdminUseCase,
    RevokeOneTimeLinkUseCase,
    ShareAccessUseCase,
    UnshareAccessUseCase,
    UpdatePasswordUseCase,
)
from shared_kernel.adapters.primary.dependencies import get_session
from shared_kernel.adapters.secondary.utc_time_gateway import UtcTimeGateway
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_vault_status_api,
)
from vault_management_context.adapters.primary.private_api import VaultStatusApi


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


def get_group_access_gateway(
    session: Session = Depends(get_session),
) -> GroupAccessGateway:
    group_repository = SqlGroupRepository(session)
    group_member_repository = SqlGroupMemberRepository(session)
    return GroupAccessGatewayAdapter(group_repository, group_member_repository)


def get_user_info_gateway(
    user_info_api: UserInfoApi = Depends(get_user_info_api),
) -> UserInfoGateway:
    return IamUserInfoGateway(user_info_api)


def get_password_vault_access_gateway(
    vault_status_api: VaultStatusApi = Depends(get_vault_status_api),
) -> PasswordVaultAccessGateway:
    return PrivateApiPasswordVaultAccessGateway(vault_status_api)


def get_one_time_link_repository(
    session: Session = Depends(get_session),
) -> OneTimeLinkRepository:
    return SqlOneTimeLinkRepository(session)


def get_time_gateway() -> TimeGateway:
    return UtcTimeGateway()


def get_event_publisher(request: Request) -> DomainEventPublisher:
    return request.app.state.domain_event_publisher


def get_create_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_encryption_gateway: PasswordEncryptionGateway = Depends(get_password_encryption_gateway),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
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
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_encryption_gateway: PasswordEncryptionGateway = Depends(get_password_encryption_gateway),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
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
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_encryption_gateway: PasswordEncryptionGateway = Depends(get_password_encryption_gateway),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
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
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
):
    return ListPasswordsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
    )


def get_delete_password_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
):
    return DeletePasswordUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
        one_time_link_repository,
    )


def get_share_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
):
    return ShareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_unshare_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
):
    return UnshareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
        password_event_repository,
    )


def get_list_resource_access_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
):
    return ListAccessUseCase(password_repository, password_permissions_repository, group_access_gateway)


def get_list_password_events_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
    password_vault_access_gateway: PasswordVaultAccessGateway = Depends(get_password_vault_access_gateway),
    user_info_gateway: UserInfoGateway = Depends(get_user_info_gateway),
):
    return ListPasswordEventsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
        password_vault_access_gateway,
        user_info_gateway,
    )


def get_password_statistic_for_admin_usecase(
    password_repository: PasswordRepository = Depends(get_password_repository),
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return GetPasswordStatisticForAdminUseCase(password_repository, one_time_link_repository, time_gateway)


def get_password_ownership_service(
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_permissions_repository: PasswordPermissionsRepository = Depends(get_password_permissions_repository),
    group_access_gateway: GroupAccessGateway = Depends(get_group_access_gateway),
) -> PasswordOwnershipService:
    return PasswordOwnershipService(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
    )


def get_create_one_time_link_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    ownership_service: PasswordOwnershipService = Depends(get_password_ownership_service),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return CreateOneTimeLinkUseCase(
        one_time_link_repository,
        ownership_service,
        password_event_repository,
        time_gateway,
    )


def get_consume_one_time_link_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    password_repository: PasswordRepository = Depends(get_password_repository),
    password_encryption_gateway: PasswordEncryptionGateway = Depends(get_password_encryption_gateway),
    password_vault_access_gateway: PasswordVaultAccessGateway = Depends(get_password_vault_access_gateway),
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return ConsumeOneTimeLinkUseCase(
        one_time_link_repository,
        password_repository,
        password_encryption_gateway,
        password_vault_access_gateway,
        password_event_repository,
        time_gateway,
    )


def get_list_one_time_links_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    ownership_service: PasswordOwnershipService = Depends(get_password_ownership_service),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return ListOneTimeLinksUseCase(one_time_link_repository, ownership_service, time_gateway)


def get_revoke_one_time_link_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    ownership_service: PasswordOwnershipService = Depends(get_password_ownership_service),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return RevokeOneTimeLinkUseCase(one_time_link_repository, ownership_service, time_gateway)


def get_list_password_events_by_actor_usecase(
    password_event_repository: PasswordEventRepository = Depends(get_password_event_repository),
):
    return ListPasswordEventsByActorUseCase(password_event_repository)


def get_one_time_link_audit_assembler(
    password_repository: PasswordRepository = Depends(get_password_repository),
    user_info_gateway: UserInfoGateway = Depends(get_user_info_gateway),
) -> OneTimeLinkAuditAssembler:
    return OneTimeLinkAuditAssembler(password_repository, user_info_gateway)


def get_list_one_time_links_for_admin_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    audit_assembler: OneTimeLinkAuditAssembler = Depends(get_one_time_link_audit_assembler),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return ListOneTimeLinksForAdminUseCase(one_time_link_repository, audit_assembler, time_gateway)


def get_list_my_one_time_links_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    audit_assembler: OneTimeLinkAuditAssembler = Depends(get_one_time_link_audit_assembler),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return ListMyOneTimeLinksUseCase(one_time_link_repository, audit_assembler, time_gateway)


def get_revoke_one_time_link_for_admin_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return RevokeOneTimeLinkForAdminUseCase(one_time_link_repository, time_gateway)


def get_revoke_all_one_time_links_for_user_usecase(
    one_time_link_repository: OneTimeLinkRepository = Depends(get_one_time_link_repository),
    time_gateway: TimeGateway = Depends(get_time_gateway),
):
    return RevokeAllOneTimeLinksForUserUseCase(one_time_link_repository, time_gateway)
