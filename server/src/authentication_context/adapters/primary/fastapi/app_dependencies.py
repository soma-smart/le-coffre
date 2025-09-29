from fastapi import Depends
from starlette.requests import Request

from authentication_context.application.use_cases import (
    RegisterAdminWithPasswordUseCase,
    AdminLoginUseCase,
    ValidateUserTokenUseCase,
)
from authentication_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
    TokenGateway,
    SessionRepository,
    UserManagementGateway,
)


def get_user_password_repository(request: Request) -> UserPasswordRepository:
    return request.app.state.user_password_repository


def get_password_hashing_gateway(request: Request) -> PasswordHashingGateway:
    return request.app.state.password_hashing_gateway


def get_token_gateway(request: Request) -> TokenGateway:
    return request.app.state.token_gateway


def get_session_repository(request: Request) -> SessionRepository:
    return request.app.state.session_repository


def get_user_management_gateway(request: Request) -> UserManagementGateway:
    return request.app.state.user_management_gateway


def get_register_admin_usecase(
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


def get_admin_login_usecase(
    user_password_repository: UserPasswordRepository = Depends(
        get_user_password_repository
    ),
    password_hashing_gateway: PasswordHashingGateway = Depends(
        get_password_hashing_gateway
    ),
    token_gateway: TokenGateway = Depends(get_token_gateway),
    session_repository: SessionRepository = Depends(get_session_repository),
):
    return AdminLoginUseCase(
        user_password_repository,
        password_hashing_gateway,
        token_gateway,
        session_repository,
    )


def get_validate_token_usecase(
    user_password_repository: UserPasswordRepository = Depends(
        get_user_password_repository
    ),
    token_gateway: TokenGateway = Depends(get_token_gateway),
    session_repository: SessionRepository = Depends(get_session_repository),
):
    return ValidateUserTokenUseCase(
        user_password_repository,
        token_gateway,
        session_repository,
    )
