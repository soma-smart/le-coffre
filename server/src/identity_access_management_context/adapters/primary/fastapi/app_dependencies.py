from fastapi import Depends
from starlette.requests import Request

from identity_access_management_context.application.use_cases import (
    GetUserUseCase,
    GetUserMeUseCase,
    DeleteUserUseCase,
    UpdateUserUseCase,
    CreateUserUseCase,
    ListUserUseCase,
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
)
from identity_access_management_context.application.gateways import (
    UserRepository,
    UserPasswordRepository,
    PasswordHashingGateway,
    TokenGateway,
    SsoGateway,
    SsoUserRepository,
    SsoConfigurationRepository,
    GroupRepository,
    GroupMemberRepository,
)
from shared_kernel.time import TimeProvider
from shared_kernel.encryption import EncryptionService


def get_group_repository(request: Request) -> GroupRepository:
    return request.app.state.group_repository


def get_group_member_repository(request: Request) -> GroupMemberRepository:
    return request.app.state.group_member_repository


def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repository


def get_user_password_repository(request: Request) -> UserPasswordRepository:
    return request.app.state.user_password_repository


def get_password_hashing_gateway(request: Request) -> PasswordHashingGateway:
    return request.app.state.password_hashing_gateway


def get_token_gateway(request: Request) -> TokenGateway:
    return request.app.state.token_gateway


def get_sso_gateway(request: Request) -> SsoGateway:
    return request.app.state.sso_gateway


def get_sso_user_repository(request: Request) -> SsoUserRepository:
    return request.app.state.sso_user_repository


def get_sso_configuration_repository(request: Request) -> SsoConfigurationRepository:
    return request.app.state.sso_configuration_repository


def get_time_provider(request: Request) -> TimeProvider:
    return request.app.state.time_provider


def get_encryption_service(request: Request) -> EncryptionService:
    return request.app.state.encryption_service


# User Management Use Cases
def get_get_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return GetUserUseCase(user_repository)


def get_delete_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return DeleteUserUseCase(user_repository)


def get_update_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return UpdateUserUseCase(user_repository)


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
):
    return GetUserMeUseCase(user_repository)


# Authentication Use Cases
def get_admin_login_usecase(
    user_password_repository: UserPasswordRepository = Depends(
        get_user_password_repository
    ),
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
    token_gateway: TokenGateway = Depends(get_token_gateway),
    time_provider: TimeProvider = Depends(get_time_provider),
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
    encryption_service: EncryptionService = Depends(get_encryption_service),
):
    return GetSsoAuthorizeUrlUseCase(
        sso_gateway, sso_configuration_repository, encryption_service
    )


# Alias for backward compatibility
get_sso_url_usecase = get_sso_authorize_url_usecase


def get_configure_sso_provider_usecase(
    sso_gateway: SsoGateway = Depends(get_sso_gateway),
    sso_configuration_repository: SsoConfigurationRepository = Depends(
        get_sso_configuration_repository
    ),
    encryption_service: EncryptionService = Depends(get_encryption_service),
):
    return ConfigureSsoProviderUseCase(
        sso_gateway, sso_configuration_repository, encryption_service
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
    time_provider: TimeProvider = Depends(get_time_provider),
    group_repository: GroupRepository = Depends(get_group_repository),
    group_member_repository: GroupMemberRepository = Depends(
        get_group_member_repository
    ),
    sso_configuration_repository: SsoConfigurationRepository = Depends(
        get_sso_configuration_repository
    ),
    encryption_service: EncryptionService = Depends(get_encryption_service),
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
        encryption_service,
    )


def get_refresh_access_token_usecase(
    token_gateway: TokenGateway = Depends(get_token_gateway),
    user_repository: UserRepository = Depends(get_user_repository),
    time_provider: TimeProvider = Depends(get_time_provider),
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
