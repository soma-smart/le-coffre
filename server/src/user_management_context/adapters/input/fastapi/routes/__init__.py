from fastapi import APIRouter
from . import (
    user_get_routes,
    user_delete_routes,
    user_create_routes,
    user_update_routes,
    user_list_routes,
)


def get_user_management_router():
    user_management_router = APIRouter()

    user_management_router.include_router(user_get_routes.router)
    user_management_router.include_router(user_delete_routes.router)
    user_management_router.include_router(user_create_routes.router)
    user_management_router.include_router(user_update_routes.router)
    user_management_router.include_router(user_list_routes.router)

    return user_management_router
