from fastapi import APIRouter
from .user import (
    user_get_routes,
    user_delete_routes,
    user_create_routes,
    user_update_routes,
    user_list_routes,
)

from .admin import (
    admin_login_route,
    register_admin_with_password_route,
)

from .sso import (
    configure_sso_provider_route,
    get_sso_url_route,
    sso_callback_route,
)


def get_user_management_router():
    user_management_router = APIRouter()

    user_management_router.include_router(user_get_routes.router)
    user_management_router.include_router(user_delete_routes.router)
    user_management_router.include_router(user_create_routes.router)
    user_management_router.include_router(user_update_routes.router)
    user_management_router.include_router(user_list_routes.router)

    return user_management_router


def get_authentication_router():
    authentication_router = APIRouter()

    authentication_router.include_router(admin_login_route.router)
    authentication_router.include_router(register_admin_with_password_route.router)
    authentication_router.include_router(configure_sso_provider_route.router)
    authentication_router.include_router(get_sso_url_route.router)
    authentication_router.include_router(sso_callback_route.router)

    return authentication_router
