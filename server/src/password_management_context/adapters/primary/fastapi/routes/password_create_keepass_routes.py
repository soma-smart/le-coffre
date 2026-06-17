import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from typing_extensions import Annotated

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_passwords_from_keepass_usecase,
)
from password_management_context.application.commands.create_password_from_keepass_command import (
    CreatePasswordsFromKeepassCommand,
)
from password_management_context.application.use_cases.create_password_from_keepass_use_case import (
    CreatePasswordsFromKeepassUseCase,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities.validated_user import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class CreatePasswordsFromKeepassResponse(BaseModel):
    ids: list[UUID]


@router.post(
    "/keepass",
    response_model=CreatePasswordsFromKeepassResponse,
    status_code=201,
    summary="Create passwords from KeePass file",
    responses={
        400: {"description": "Invalid KeePass file or password"},
        503: {"description": "Vault is locked"},
    },
)
def create_passwords_from_keepass(
    file: Annotated[UploadFile, File(...)],
    password: Annotated[str, Form(...)],
    group_id: Annotated[UUID, Form(...)],
    current_user: Annotated[ValidatedUser, Depends(get_current_user)],
    usecase: Annotated[
        CreatePasswordsFromKeepassUseCase,
        Depends(get_create_passwords_from_keepass_usecase),
    ],
):
    try:
        filename = file.filename

        if not filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")

        if not filename.endswith(".kdbx"):
            raise HTTPException(status_code=400, detail="Le fichier doit être un .kdbx")

        command = CreatePasswordsFromKeepassCommand(
            user_id=current_user.user_id,
            group_id=group_id,
            filename=filename,
            content=file.file.read(),
            master_password=password,
        )

        created_password_ids = usecase.execute(command)

        return CreatePasswordsFromKeepassResponse(ids=created_password_ids)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in create passwords from KeePass")
        raise HTTPException(status_code=500, detail="Internal server error") from e
