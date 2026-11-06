from sqlmodel import Session

from fastapi import Depends, Request
from notification_context.adapters.secondary import PrivateApiOneTimeLinkGateway
from notification_context.adapters.secondary.sql import (
    SqlNotificationPreferencesRepository,
    SqlOneTimeLinkSubscriptionRepository,
)
from notification_context.application.gateways import (
    NotificationPreferencesRepository,
    OneTimeLinkGateway,
    OneTimeLinkSubscriptionRepository,
)
from notification_context.application.use_cases import (
    GetNotificationPreferencesUseCase,
    SubscribeToOneTimeLinkUseCase,
    UpdateNotificationPreferencesUseCase,
)
from password_management_context.adapters.primary.private_api import OneTimeLinkInfoApi
from shared_kernel.adapters.primary.dependencies import get_session
from shared_kernel.adapters.secondary.utc_time_gateway import UtcTimeGateway


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


def get_one_time_link_subscription_repository(
    session: Session = Depends(get_session),
) -> OneTimeLinkSubscriptionRepository:
    return SqlOneTimeLinkSubscriptionRepository(session)


def get_one_time_link_gateway(request: Request) -> OneTimeLinkGateway:
    return PrivateApiOneTimeLinkGateway(OneTimeLinkInfoApi(session_maker=request.app.state.session_maker))


def get_subscribe_to_one_time_link_usecase(
    repository: OneTimeLinkSubscriptionRepository = Depends(get_one_time_link_subscription_repository),
    one_time_link_gateway: OneTimeLinkGateway = Depends(get_one_time_link_gateway),
) -> SubscribeToOneTimeLinkUseCase:
    return SubscribeToOneTimeLinkUseCase(repository, one_time_link_gateway, UtcTimeGateway())
