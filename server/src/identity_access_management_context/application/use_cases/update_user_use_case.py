from uuid import UUID

from identity_access_management_context.application.commands import UpdateUserCommand
from identity_access_management_context.application.gateways import (
    PasswordCredentialRecordRepository,
    UserEventRepository,
    UserRepository,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.events import UserUpdatedEvent
from identity_access_management_context.domain.exceptions import (
    EmailAlreadyUsedException,
    UserNotFoundError,
    UserUpdateNotAllowedException,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class UpdateUserUseCase(TracedUseCase):
    def __init__(
        self,
        user_repository: UserRepository,
        password_credential_record_repository: PasswordCredentialRecordRepository,
        event_publisher: DomainEventPublisher,
        user_event_repository: UserEventRepository,
    ):
        self.user_repository = user_repository
        self._password_credential_record_repository = password_credential_record_repository
        self._event_publisher = event_publisher
        self._user_event_repository = user_event_repository

    def execute(self, command: UpdateUserCommand) -> UUID:
        requesting_user = command.requesting_user
        if requesting_user.user_id != command.id and not AdminPermissionChecker.is_admin(requesting_user):
            raise UserUpdateNotAllowedException(requesting_user.user_id, command.id)

        user = self.user_repository.get_by_id(command.id)
        if not user:
            raise UserNotFoundError(command.id)

        previous_email = user.email
        email_changes = command.email != previous_email
        if email_changes:
            self._ensure_email_is_free(user.id, command.email)

        user.username = command.username
        user.email = command.email
        user.name = command.name

        # The password the user logs in with is found by the email the app shows them:
        # both change together, or the account shows one address and only accepts the other.
        # Unless the user already logs in with the new email: that login then serves as is.
        follows_email = (
            email_changes
            and self._has_password_login_on(user, previous_email)
            and not self._has_password_login_on(user, command.email)
        )
        if follows_email:
            self._password_credential_record_repository.update_email(user.id, previous_email, command.email)

        try:
            self.user_repository.update(user)
        except Exception:
            if follows_email:
                self._password_credential_record_repository.update_email(user.id, command.email, previous_email)
            raise

        event = UserUpdatedEvent(
            user_id=command.id,
            updated_by_principal_id=requesting_user.user_id,
        )
        self._event_publisher.publish(event)
        self._user_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_principal_id=requesting_user.user_id,
            event_data={"user_id": str(command.id)},
        )

        return user.id

    def _ensure_email_is_free(self, user_id: UUID, email: str) -> None:
        """Refuse an email another account shows, or logs in with."""
        if self.user_repository.get_by_email(email) is not None:
            raise EmailAlreadyUsedException(email)

        credential_record = self._password_credential_record_repository.get_by_email(email)
        if credential_record is not None and credential_record.principal_id != user_id:
            raise EmailAlreadyUsedException(email)

    def _has_password_login_on(self, user: User, email: str) -> bool:
        """Whether the user logs in with a password under this email.

        Checked against the owner: only this user's own login may follow its email.
        """
        credential_record = self._password_credential_record_repository.get_by_email(email)
        return credential_record is not None and credential_record.principal_id == user.id
