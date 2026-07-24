from datetime import datetime
from uuid import UUID

from password_management_context.application.gateways import OneTimeLinkRepository
from shared_kernel.application.gateways import TimeGateway


class OneTimeLinkRevocationApi:
    """Lets another context cut the links a user issued.

    Exposed as a private API rather than through the domain event bus because
    nothing subscribes to that bus today: UserDeletedEvent is published and no
    handler exists, so a link revocation routed through it would never run.
    """

    def __init__(self, one_time_link_repository: OneTimeLinkRepository, time_gateway: TimeGateway):
        self._one_time_link_repository = one_time_link_repository
        self._time_gateway = time_gateway

    def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke every still-redeemable link issued by this user, returning the count."""
        now: datetime = self._time_gateway.get_current_time()
        return self._one_time_link_repository.revoke_all_for_creator(user_id, now)
