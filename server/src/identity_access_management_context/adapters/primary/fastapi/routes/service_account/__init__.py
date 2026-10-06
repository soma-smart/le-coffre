from .create import router as service_account_create_router
from .list import router as service_account_list_router
from .revoke import router as service_account_revoke_router
from .rotate import router as service_account_rotate_token_router

__all__ = [
    "service_account_create_router",
    "service_account_list_router",
    "service_account_rotate_token_router",
    "service_account_revoke_router",
]
