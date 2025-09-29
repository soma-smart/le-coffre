from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from rights_access_context.adapters.primary.fastapi.app_dependencies import (
    get_share_access_usecase,
)
from rights_access_context.application.use_cases import ShareAccessUseCase
from rights_access_context.application.commands import ShareResourceCommand
from rights_access_context.domain.exceptions import (
    PermissionDeniedError,
    RightAccessDomainError,
)

router = APIRouter(tags=["Access Rights"])


class ShareAccessRequest(BaseModel):
    from_id: UUID
    to_id: UUID


@router.post(
    "/{resource_id}/share",
    status_code=201,
    summary="Share access to a password",
)
def share_access(
    resource_id: UUID,
    request: ShareAccessRequest,
    usecase: ShareAccessUseCase = Depends(get_share_access_usecase),
):
    """
    Share access to a resource.

    - **resource_id**: The ID of the resource to share
    - **from_id**: The ID of the user sharing the resource
    - **to_id**: The ID of the user receiving access
    """
    try:
        command = ShareResourceCommand(
            owner_id=request.from_id, user_id=request.to_id, resource_id=resource_id
        )
        usecase.execute(command)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RightAccessDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")
