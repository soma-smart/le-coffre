from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_password_usecase,
)
from password_management_context.application.use_cases import GetPasswordUseCase
from password_management_context.domain.exceptions import (
    PasswordManagementDomainError,
    PasswordNotFoundError,
)
from shared_kernel.access_control.exceptions import AccessDeniedError

router = APIRouter(prefix="/api/passwords", tags=["Password Management"])


class GetPasswordResponse(BaseModel):
    id: UUID
    name: str
    decrypted_password: str
    folder: str | None = None


@router.get(
    "/{password_id}",
    response_model=GetPasswordResponse,
    status_code=200,
    summary="Get a password by ID",
)
def get_password(
    password_id: UUID,
    user_id: UUID,
    usecase: GetPasswordUseCase = Depends(get_get_password_usecase),
):
    """
    Retrieve a password by its ID with user authentication.

    - **password_id**: The ID of the password to retrieve
    - **user_id**: ID of the user requesting access
    """
    try:
        password_response = usecase.execute(user_id, password_id)

        return GetPasswordResponse(
            id=password_response.id,
            name=password_response.name,
            decrypted_password=password_response.decrypted_password,
            folder=password_response.folder,
        )
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")
