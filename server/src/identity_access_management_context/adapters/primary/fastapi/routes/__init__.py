from fastapi import APIRouter

from . import refresh_access_token_routes
from .admin import (
    admin_login_route,
    register_admin_with_password_route,
)
from .group import (
    get_group_router,
    group_add_member_router,
    group_add_owner_router,
    group_create_router,
    group_delete_router,
    group_remove_member_router,
    group_update_router,
    list_groups_router,
)
from .sso import (
    configure_sso_provider_route,
    get_sso_url_route,
    is_sso_config_set_route,
    sso_callback_route,
)
from .user import (
    admin_stat_routes,
    user_create_routes,
    user_delete_routes,
    user_get_routes,
    user_list_routes,
    user_me_routes,
    user_promote_admin_routes,
    user_update_password_routes,
    user_update_routes,
)


def get_user_management_router():
    user_management_router = APIRouter()

    user_management_router.include_router(admin_stat_routes.router)
    user_management_router.include_router(user_me_routes.router)
    user_management_router.include_router(user_update_password_routes.router)
    user_management_router.include_router(user_get_routes.router)
    user_management_router.include_router(user_create_routes.router)
    user_management_router.include_router(user_promote_admin_routes.router)
    user_management_router.include_router(user_delete_routes.router)
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
    authentication_router.include_router(is_sso_config_set_route.router)
    authentication_router.include_router(refresh_access_token_routes.router)

    return authentication_router


def get_group_management_router():
    group_management_router = APIRouter()

    group_management_router.include_router(group_create_router)
    group_management_router.include_router(group_add_member_router)
    group_management_router.include_router(group_add_owner_router)
    group_management_router.include_router(group_remove_member_router)
    group_management_router.include_router(group_update_router)
    group_management_router.include_router(get_group_router)
    group_management_router.include_router(list_groups_router)
    group_management_router.include_router(group_delete_router)

    return group_management_router
