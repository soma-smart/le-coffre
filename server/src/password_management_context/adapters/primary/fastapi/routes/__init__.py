from fastapi import APIRouter
from . import password_create_routes, password_get_routes


def get_password_management_router():
    password_management_router = APIRouter()

    password_management_router.include_router(password_create_routes.router)
    password_management_router.include_router(password_get_routes.router)

    return password_management_router
