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
)
from identity_access_management_context.application.gateways import (
    UserRepository,
    UserPasswordRepository,
    PasswordHashingGateway,
    TokenGateway,
    UserManagementGateway,
    SsoGateway,
    SsoUserRepository,
)
from shared_kernel.time import TimeProvider


def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repository


def get_user_password_repository(request: Request) -> UserPasswordRepository:
    return request.app.state.user_password_repository


def get_password_hashing_gateway(request: Request) -> PasswordHashingGateway:
    return request.app.state.password_hashing_gateway


def get_token_gateway(request: Request) -> TokenGateway:
    return request.app.state.token_gateway


def get_user_management_gateway(request: Request) -> UserManagementGateway:
    return request.app.state.user_management_gateway


def get_sso_gateway(request: Request) -> SsoGateway:
    return request.app.state.sso_gateway


def get_sso_user_repository(request: Request) -> SsoUserRepository:
    return request.app.state.sso_user_repository


def get_time_provider(request: Request) -> TimeProvider:
    return request.app.state.time_provider


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
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
):
    return CreateUserUseCase(user_repository, password_hashing_gateway)


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
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
    user_management_gateway: UserManagementGateway = Depends(
        get_user_management_gateway
    ),
):
    return RegisterAdminWithPasswordUseCase(
        user_password_repository,
        password_hashing_gateway,
        user_management_gateway,
    )


# Alias for backward compatibility
get_register_admin_usecase = get_register_admin_with_password_usecase


def get_sso_authorize_url_usecase(
    sso_gateway: SsoGateway = Depends(get_sso_gateway),
):
    return GetSsoAuthorizeUrlUseCase(sso_gateway)


# Alias for backward compatibility
get_sso_url_usecase = get_sso_authorize_url_usecase


def get_configure_sso_provider_usecase(
    sso_gateway: SsoGateway = Depends(get_sso_gateway),
):
    return ConfigureSsoProviderUseCase(sso_gateway)


def get_sso_login_usecase(
    sso_gateway: SsoGateway = Depends(get_sso_gateway),
    sso_user_repository: SsoUserRepository = Depends(get_sso_user_repository),
    user_management_gateway: UserManagementGateway = Depends(
        get_user_management_gateway
    ),
    token_gateway: TokenGateway = Depends(get_token_gateway),
    time_provider: TimeProvider = Depends(get_time_provider),
):
    return SsoLoginUseCase(
        sso_gateway,
        sso_user_repository,
        user_management_gateway,
        token_gateway,
        time_provider,
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
