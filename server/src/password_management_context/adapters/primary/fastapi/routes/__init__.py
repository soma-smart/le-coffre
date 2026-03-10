from fastapi import APIRouter

from . import (
    list_password_access_routes,
    password_create_routes,
    password_delete_routes,
    password_events_list_routes,
    password_get_routes,
    password_update_routes,
    passwords_list_routes,
    share_password_routes,
    unshare_password_routes,
)


def get_password_management_router():
    password_management_router = APIRouter()

    password_management_router.include_router(password_create_routes.router)
    password_management_router.include_router(passwords_list_routes.router)  # Must come before password_get_routes
    password_management_router.include_router(password_events_list_routes.router)
    password_management_router.include_router(password_get_routes.router)
    password_management_router.include_router(password_delete_routes.router)
    password_management_router.include_router(password_update_routes.router)
    password_management_router.include_router(share_password_routes.router)
    password_management_router.include_router(unshare_password_routes.router)
    password_management_router.include_router(list_password_access_routes.router)

    return password_management_router
