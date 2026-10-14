from fastapi import APIRouter

from . import (
    notification_preferences_get_routes,
    notification_preferences_update_routes,
    one_time_link_subscription_routes,
)


def get_notification_router() -> APIRouter:
    notification_router = APIRouter()
    notification_router.include_router(notification_preferences_get_routes.router)
    notification_router.include_router(notification_preferences_update_routes.router)
    notification_router.include_router(one_time_link_subscription_routes.router)
    return notification_router
