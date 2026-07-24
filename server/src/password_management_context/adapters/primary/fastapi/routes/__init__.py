from fastapi import APIRouter

from . import (
    list_password_access_routes,
    one_time_link_admin_routes,
    one_time_link_routes,
    password_admin_statistic_routes,
    password_create_routes,
    password_delete_routes,
    password_events_by_actor_routes,
    password_events_list_routes,
    password_get_routes,
    password_update_routes,
    passwords_list_routes,
    share_password_routes,
    unshare_password_routes,
)


def get_password_management_router():
    password_management_router = APIRouter()

    password_management_router.include_router(password_admin_statistic_routes.router)
    password_management_router.include_router(password_create_routes.router)
    password_management_router.include_router(passwords_list_routes.router)  # Must come before password_get_routes
    password_management_router.include_router(password_events_list_routes.router)
    password_management_router.include_router(password_events_by_actor_routes.router)
    # Sits before password_get_routes: its paths are more specific than /{password_id}
    password_management_router.include_router(one_time_link_routes.owner_router)
    # Before public_router: its /one-time-links/{link_id} route would otherwise
    # swallow /one-time-links/mine and try to parse "mine" as a UUID.
    password_management_router.include_router(one_time_link_admin_routes.mine_router)
    password_management_router.include_router(one_time_link_admin_routes.admin_router)
    password_management_router.include_router(one_time_link_routes.public_router)
    password_management_router.include_router(password_get_routes.router)
    password_management_router.include_router(password_delete_routes.router)
    password_management_router.include_router(password_update_routes.router)
    password_management_router.include_router(share_password_routes.router)
    password_management_router.include_router(unshare_password_routes.router)
    password_management_router.include_router(list_password_access_routes.router)

    return password_management_router
