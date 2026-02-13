from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.application.gateways import CsrfTokenGateway
from shared_kernel.domain.entities import ValidatedUser


router = APIRouter(prefix="/auth", tags=["Authentication"])


class CsrfTokenResponse(BaseModel):
    csrf_token: str


def get_csrf_token_gateway_dependency(request: Request) -> CsrfTokenGateway:
    """Dependency to get CSRF token gateway from app state."""
    return request.app.state.csrf_token_gateway


@router.get(
    "/csrf-token",
    status_code=200,
    response_model=CsrfTokenResponse,
    summary="Get CSRF token",
)
async def get_csrf_token(
    current_user: ValidatedUser = Depends(get_current_user),
    csrf_gateway: CsrfTokenGateway = Depends(get_csrf_token_gateway_dependency),
):
    """
    Get a CSRF token for the current authenticated user.

    This endpoint must be called after successful authentication to obtain
    a CSRF token. The token must be included in the X-CSRF-Token header
    for all mutating requests (POST, PUT, DELETE, PATCH).

    - **Authorization**: Requires valid access_token cookie

    Returns a CSRF token that remains valid for the entire session.
    """
    token = csrf_gateway.generate_token(current_user.user_id)
    return CsrfTokenResponse(csrf_token=token)
