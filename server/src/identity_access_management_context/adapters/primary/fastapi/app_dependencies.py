from fastapi import Depends
from starlette.requests import Request
from sqlmodel import Session

from identity_access_management_context.application.use_cases import (
    GetUserUseCase,
    GetUserMeUseCase,
    DeleteUserUseCase,
    UpdateUserUseCase,
    UpdateUserPasswordUseCase,
    CreateUserUseCase,
    ListUserUseCase,
    PromoteAdminUseCase,
    AdminLoginUseCase,
    RegisterAdminWithPasswordUseCase,
    GetSsoAuthorizeUrlUseCase,
    ConfigureSsoProviderUseCase,
    SsoLoginUseCase,
    RefreshAccessTokenUseCase,
    CreateGroupUseCase,
    AddUserToGroupUseCase,
    AddOwnerToGroupUseCase,
    RemoveUserFromGroupUseCase,
    GetGroupUseCase,
    ListGroupsUseCase,
    UpdateGroupUseCase,
    IsSsoConfigSetUseCase,
    DeleteGroupUseCase,
)
from identity_access_management_context.adapters.primary.private_api import (
    UserInfoApi,
)
from identity_access_management_context.application.gateways import (
    UserRepository,
    UserPasswordRepository,
    PasswordHashingGateway,
    TokenGateway,
    SsoGateway,
    SsoUserRepository,
    SsoConfigurationRepository,
    SsoEncryptionGateway,
    GroupRepository,
    GroupMemberRepository,
    GroupUsageGateway,
)
from identity_access_management_context.adapters.secondary.sql import (
    SqlUserRepository,
    SqlUserPasswordRepository,
    SqlGroupRepository,
    SqlGroupMemberRepository,
    SqlSsoUserRepository,
    SqlSsoConfigurationRepository,
)
from identity_access_management_context.adapters.secondary.private_api import (
    PrivateApiGroupUsageGateway,
)
from password_management_context.adapters.secondary import (
    SqlPasswordPermissionsRepository,
)
from password_management_context.application.use_cases import IsGroupUsedUseCase
from password_management_context.adapters.primary.private_api import GroupUsageApi
from shared_kernel.application.gateways import TimeGateway, DomainEventPublisher
from shared_kernel.adapters.primary.dependencies import get_session


def get_group_repository(session: Session = Depends(get_session)) -> GroupRepository:
    return SqlGroupRepository(session)


def get_group_member_repository(
    session: Session = Depends(get_session),
) -> GroupMemberRepository:
    return SqlGroupMemberRepository(session)


def get_group_usage_gateway(
    session: Session = Depends(get_session),
) -> GroupUsageGateway:
    # Create the password permissions repository with session
    password_permissions_repository = SqlPasswordPermissionsRepository(session)
    # Create the use case
    is_group_used_use_case = IsGroupUsedUseCase(password_permissions_repository)
    # Create the API
    group_usage_api = GroupUsageApi(is_group_used_use_case)
    # Create and return the gateway
    return PrivateApiGroupUsageGateway(group_usage_api)


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return SqlUserRepository(session)


def get_user_password_repository(
    session: Session = Depends(get_session),
) -> UserPasswordRepository:
    return SqlUserPasswordRepository(session)


def get_sso_user_repository(
    session: Session = Depends(get_session),
) -> SsoUserRepository:
    return SqlSsoUserRepository(session)


def get_sso_configuration_repository(
    session: Session = Depends(get_session),
) -> SsoConfigurationRepository:
    return SqlSsoConfigurationRepository(session)


def get_password_hashing_gateway(request: Request) -> PasswordHashingGateway:
    return request.app.state.password_hashing_gateway


def get_token_gateway(request: Request) -> TokenGateway:
    return request.app.state.token_gateway


def get_sso_gateway(request: Request) -> SsoGateway:
    return request.app.state.sso_gateway


def get_time_provider(request: Request) -> TimeGateway:
    return request.app.state.time_provider


def get_sso_encryption_gateway(request: Request) -> SsoEncryptionGateway:
    return request.app.state.sso_encryption_gateway


def get_event_publisher(request: Request) -> DomainEventPublisher:
    return request.app.state.domain_event_publisher


# User Management Use Cases
def get_get_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return GetUserUseCase(user_repository)


def get_delete_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
):
    return DeleteUserUseCase(
        user_repository,
        group_repository,
        group_member_repository,
        event_publisher,
    )


def get_promote_admin_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return PromoteAdminUseCase(user_repository)


def get_update_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return UpdateUserUseCase(user_repository)


def get_update_user_password_usecase(
    user_password_repository: UserPasswordRepository = Depends(
        get_user_password_repository
    ),
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
):
    return UpdateUserPasswordUseCase(
        user_password_repository,
        password_hashing_gateway,
    )


def get_create_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
    user_password_repository: UserPasswordRepository = Depends(
        get_user_password_repository
    ),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
):
    return CreateUserUseCase(
        user_repository,
        user_password_repository,
        group_repository,
        group_member_repository,
        password_hashing_gateway,
    )


def get_list_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return ListUserUseCase(user_repository)


def get_get_user_me_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
    sso_user_repository: SsoUserRepository = Depends(get_sso_user_repository),
):
    return GetUserMeUseCase(user_repository, sso_user_repository)


# Authentication Use Cases
def get_admin_login_usecase(
    user_password_repository: UserPasswordRepository = Depends(
        get_user_password_repository
    ),
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
    token_gateway: TokenGateway = Depends(get_token_gateway),
    time_provider: TimeGateway = Depends(get_time_provider),
):
    return AdminLoginUseCase(
        user_password_repository,
        password_hashing_gateway,
        token_gateway,
        time_provider,
    )


def get_register_admin_with_password_usecase(
    user_password_repository: UserPasswordRepository = Depends(
        get_user_password_repository
    ),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
    user_repository: UserRepository = Depends(get_user_repository),
):
    return RegisterAdminWithPasswordUseCase(
        user_password_repository,
        password_hashing_gateway,
        user_repository,
        group_repository,
        group_member_repository,
    )


# Alias for backward compatibility
get_register_admin_usecase = get_register_admin_with_password_usecase


def get_sso_authorize_url_usecase(
    sso_gateway: SsoGateway = Depends(get_sso_gateway),
    sso_configuration_repository: SsoConfigurationRepository = Depends(
        get_sso_configuration_repository
    ),
    sso_encryption_gateway: SsoEncryptionGateway = Depends(get_sso_encryption_gateway),
):
    return GetSsoAuthorizeUrlUseCase(
        sso_gateway, sso_configuration_repository, sso_encryption_gateway
    )


# Alias for backward compatibility
get_sso_url_usecase = get_sso_authorize_url_usecase


def get_configure_sso_provider_usecase(
    sso_gateway: SsoGateway = Depends(get_sso_gateway),
    sso_configuration_repository: SsoConfigurationRepository = Depends(
        get_sso_configuration_repository
    ),
    sso_encryption_gateway: SsoEncryptionGateway = Depends(get_sso_encryption_gateway),
):
    return ConfigureSsoProviderUseCase(
        sso_gateway, sso_configuration_repository, sso_encryption_gateway
    )


def get_is_sso_config_set_usecase(
    sso_configuration_repository: SsoConfigurationRepository = Depends(
        get_sso_configuration_repository
    ),
):
    return IsSsoConfigSetUseCase(sso_configuration_repository)


def get_sso_login_usecase(
    sso_gateway: SsoGateway = Depends(get_sso_gateway),
    sso_user_repository: SsoUserRepository = Depends(get_sso_user_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
    token_gateway: TokenGateway = Depends(get_token_gateway),
    time_provider: TimeGateway = Depends(get_time_provider),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
    sso_configuration_repository: SsoConfigurationRepository = Depends(
        get_sso_configuration_repository
    ),
    sso_encryption_gateway: SsoEncryptionGateway = Depends(get_sso_encryption_gateway),
):
    return SsoLoginUseCase(
        sso_gateway,
        sso_user_repository,
        user_repository,
        password_hashing_gateway,
        token_gateway,
        time_provider,
        group_repository,
        group_member_repository,
        sso_configuration_repository,
        sso_encryption_gateway,
    )


def get_refresh_access_token_usecase(
    token_gateway: TokenGateway = Depends(get_token_gateway),
    user_repository: UserRepository = Depends(get_user_repository),
    time_provider: TimeGateway = Depends(get_time_provider),
):
    return RefreshAccessTokenUseCase(
        token_gateway,
        user_repository,
        time_provider,
    )


# Group Management Use Cases
def get_create_group_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
):
    return CreateGroupUseCase(
        user_repository,
        group_repository,
        group_member_repository,
    )


def get_add_user_to_group_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
):
    return AddUserToGroupUseCase(
        user_repository,
        group_repository,
        group_member_repository,
    )


def get_add_owner_to_group_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
):
    return AddOwnerToGroupUseCase(
        user_repository,
        group_repository,
        group_member_repository,
    )


def get_remove_user_from_group_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
):
    return RemoveUserFromGroupUseCase(
        user_repository,
        group_repository,
        group_member_repository,
    )


def get_get_group_usecase(
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
):
    return GetGroupUseCase(group_repository, group_member_repository)


def get_user_info_api(
    get_user_usecase: GetUserUseCase = Depends(get_get_user_usecase),
    get_group_usecase: GetGroupUseCase = Depends(get_get_group_usecase),
) -> UserInfoApi:
    """Private API for other contexts to query user information"""
    return UserInfoApi(get_user_usecase, get_group_usecase)


def get_list_groups_usecase(
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
):
    return ListGroupsUseCase(group_repository, group_member_repository)


def get_update_group_usecase(
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
):
    return UpdateGroupUseCase(group_repository, group_member_repository)


def get_delete_group_usecase(
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
    group_usage_gateway: GroupUsageGateway = Depends(get_group_usage_gateway),
):
    return DeleteGroupUseCase(
        group_repository, group_member_repository, group_usage_gateway
    )
