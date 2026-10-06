from sqlmodel import Session

from fastapi import Depends
from notification_context.adapters.secondary.sql import SqlNotificationPreferencesRepository
from notification_context.application.gateways import NotificationPreferencesRepository
from notification_context.application.use_cases import (
    GetNotificationPreferencesUseCase,
    UpdateNotificationPreferencesUseCase,
)
from shared_kernel.adapters.primary.dependencies import get_session


def get_notification_preferences_repository(
    session: Session = Depends(get_session),
) -> NotificationPreferencesRepository:
    return SqlNotificationPreferencesRepository(session)


def get_get_notification_preferences_usecase(
    repository: NotificationPreferencesRepository = Depends(get_notification_preferences_repository),
) -> GetNotificationPreferencesUseCase:
    return GetNotificationPreferencesUseCase(repository)


def get_update_notification_preferences_usecase(
    repository: NotificationPreferencesRepository = Depends(get_notification_preferences_repository),
) -> UpdateNotificationPreferencesUseCase:
    return UpdateNotificationPreferencesUseCase(repository)
