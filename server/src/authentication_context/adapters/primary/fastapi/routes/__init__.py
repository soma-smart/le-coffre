from fastapi import APIRouter
from . import (
    register_admin_with_password_route,
    admin_login_route,
)


def get_authentication_router():
    authentication_router = APIRouter()

    authentication_router.include_router(register_admin_with_password_route.router)
    authentication_router.include_router(admin_login_route.router)

    return authentication_router
