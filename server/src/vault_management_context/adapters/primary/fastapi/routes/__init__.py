from fastapi import APIRouter
from . import (
    vault_setup_routes,
    vault_validate_setup_routes,
    vault_unlock_routes,
    vault_clear_pending_shares_routes,
    vault_lock_routes,
    vault_status_get_routes,
)


def get_vault_management_router():
    vault_management_router = APIRouter()

    vault_management_router.include_router(vault_setup_routes.router)
    vault_management_router.include_router(vault_validate_setup_routes.router)
    vault_management_router.include_router(vault_unlock_routes.router)
    vault_management_router.include_router(vault_clear_pending_shares_routes.router)
    vault_management_router.include_router(vault_lock_routes.router)
    vault_management_router.include_router(vault_status_get_routes.router)

    return vault_management_router
