import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_revoke_service_account_usecase,
)
from identity_access_management_context.application.commands import RevokeServiceAccountCommand
from identity_access_management_context.application.use_cases import RevokeServiceAccountUseCase
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import csrf_scheme, get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iam/service-accounts", tags=["Service Accounts"])


@router.delete(
    "/{service_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(csrf_scheme)],
    summary="Revoke a service account",
)
def revoke_service_account(
    service_account_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeServiceAccountUseCase = Depends(get_revoke_service_account_usecase),
) -> None:
    """
    Revoke a service account.

    Only a group owner may do this. The account stops being active but its
    row survives, so the revocation stays auditable.
    """
    try:
        command = RevokeServiceAccountCommand(
            requesting_user=current_user.to_authenticated_user(),
            service_account_id=service_account_id,
        )
        usecase.execute(command)
    except (GroupNotFoundException, ServiceAccountNotFoundException) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ServiceAccountAlreadyRevokedException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in revoke service account")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
