from fastapi import APIRouter
from . import share_access_routes


def get_rights_access_router():
    rights_access_router = APIRouter()

    rights_access_router.include_router(share_access_routes.router)

    return rights_access_router
