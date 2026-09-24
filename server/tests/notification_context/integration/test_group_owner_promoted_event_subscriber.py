from uuid import uuid4

from identity_access_management_context.adapters.primary.private_api import (
    GroupOwnershipInfoApi,
)
from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupRepository,
    SqlUserRepository,
)
from identity_access_management_context.domain.entities import Group, User
from identity_access_management_context.domain.events import OwnerAddedToGroupEvent
from notification_context.adapters.primary.events import GroupOwnerPromotedEventSubscriber
from notification_context.adapters.secondary.private_api import (
    PrivateApiGroupOwnershipGateway,
)
from notification_context.application.use_cases import NotifyGroupOwnerPromotedUseCase
from shared_kernel.adapters.secondary import SmtpEmailGateway


def test_given_promotion_event_when_handled_should_send_owner_promotion_email_end_to_end(session, session_maker, smtpd):
    user_id = uuid4()
    group_id = uuid4()
    added_by_user_id = uuid4()
    SqlUserRepository(session).save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))
    SqlGroupRepository(session).save_group(Group(id=group_id, name="Development Team", is_personal=False))

    group_ownership_info_api = GroupOwnershipInfoApi(session_maker=session_maker)
    group_ownership_gateway = PrivateApiGroupOwnershipGateway(group_ownership_info_api)
    email_gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    notify_use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    subscriber = GroupOwnerPromotedEventSubscriber(notify_use_case)

    event = OwnerAddedToGroupEvent(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)
    subscriber.handle(event)

    assert len(smtpd.messages) == 1
    message = smtpd.messages[0]
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == 'You\'re now an owner of "Development Team"'
    assert "Alice" in message.get_payload()
    assert "Development Team" in message.get_payload()
