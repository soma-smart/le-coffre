from fastapi import APIRouter

from . import notification_preferences_routes


def get_notification_router() -> APIRouter:
    notification_router = APIRouter()
    notification_router.include_router(notification_preferences_routes.router)
    return notification_router
