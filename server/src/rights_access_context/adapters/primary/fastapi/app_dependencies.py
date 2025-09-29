from fastapi import Depends
from starlette.requests import Request

from rights_access_context.application.gateways import RightsRepository
from rights_access_context.application.use_cases import ShareAccessUseCase


def get_rights_repository(request: Request) -> RightsRepository:
    return request.app.state.rights_repository


def get_share_access_usecase(
    rights_repository: RightsRepository = Depends(get_rights_repository),
):
    return ShareAccessUseCase(rights_repository)
