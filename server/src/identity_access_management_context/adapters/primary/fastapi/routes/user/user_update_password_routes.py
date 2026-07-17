import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from config import (
    get_cookie_secure_setting,
    get_jwt_access_token_expiration_seconds,
    get_jwt_refresh_token_expiration_seconds,
)
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_token_gateway,
    get_update_user_password_usecase,
    get_user_repository,
)
from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.gateways import TokenGateway, UserRepository
from identity_access_management_context.application.use_cases import (
    UpdateUserPasswordUseCase,
)
from identity_access_management_context.domain.exceptions import (
    IdentityAccessManagementDomainError,
    InvalidCredentialsException,
    UserNotFoundException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

router = APIRouter(prefix="/users", tags=["User Management"])


class UpdateUserPasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.put(
    "/me/password",
    status_code=204,
    summary="Update current user's password",
)
def update_user_password(
    request: UpdateUserPasswordRequest,
    response: Response,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UpdateUserPasswordUseCase = Depends(get_update_user_password_usecase),
    token_gateway: TokenGateway = Depends(get_token_gateway),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Update the authenticated user's password.

    - **old_password**: Current password for verification
    - **new_password**: New password to set
    - **Authentication**: Requires authentication via access_token cookie

    Returns status code 204 (No Content) on successful password update.

    Raises:
    - 401: If old password is incorrect
    - 404: If user not found
    """
    try:
        command = UpdateUserPasswordCommand(
            user_id=current_user.user_id,
            old_password=request.old_password,
            new_password=request.new_password,
        )
        usecase.execute(command)

        # Keep the current browser session alive with fresh tokens while
        # invalidating all previously issued sessions.
        user = user_repository.get_by_id(current_user.user_id)
        if not user:
            raise UserNotFoundException(current_user.user_id)

        access_token = token_gateway.generate_token(
            user_id=current_user.user_id,
            email=current_user.email,
            roles=user.roles,
            claims={"display_name": current_user.display_name},
        )
        refresh_token = token_gateway.generate_refresh_token(
            user_id=current_user.user_id,
            email=current_user.email,
            roles=user.roles,
        )
        user.current_refresh_token_jti = refresh_token.jti
        user_repository.update(user)

        is_secure = get_cookie_secure_setting()
        response.set_cookie(
            key="access_token",
            value=access_token.value,
            httponly=True,
            secure=is_secure,
            samesite="strict",
            max_age=get_jwt_access_token_expiration_seconds(),
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token.value,
            httponly=True,
            secure=is_secure,
            samesite="strict",
            max_age=get_jwt_refresh_token_expiration_seconds(),
        )
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,
            secure=is_secure,
            samesite="strict",
            max_age=get_jwt_access_token_expiration_seconds(),
        )

    except InvalidCredentialsException as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
