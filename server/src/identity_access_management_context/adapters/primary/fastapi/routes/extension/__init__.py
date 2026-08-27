from fastapi import APIRouter

from . import (
    extension_device_exchange_routes,
    extension_device_register_routes,
    extension_pairing_approve_routes,
    extension_pairing_deny_routes,
    extension_pairing_get_routes,
    extension_session_get_routes,
    extension_token_list_routes,
    extension_token_revoke_all_routes,
    extension_token_revoke_routes,
)


def get_extension_router() -> APIRouter:
    extension_router = APIRouter()

    extension_router.include_router(extension_device_register_routes.router)
    extension_router.include_router(extension_device_exchange_routes.router)
    extension_router.include_router(extension_pairing_get_routes.router)
    extension_router.include_router(extension_pairing_approve_routes.router)
    extension_router.include_router(extension_pairing_deny_routes.router)
    extension_router.include_router(extension_session_get_routes.router)

    # Collection routes before the parameterised one: FastAPI matches in
    # registration order, so `/tokens/{token_id}` first would swallow `/tokens`.
    extension_router.include_router(extension_token_list_routes.router)
    extension_router.include_router(extension_token_revoke_all_routes.router)
    extension_router.include_router(extension_token_revoke_routes.router)

    return extension_router
