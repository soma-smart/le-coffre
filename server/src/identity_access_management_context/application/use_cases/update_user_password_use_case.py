from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    AuthSessionRepository,
    PasswordCredentialRecordRepository,
    PasswordHashingGateway,
    TokenCredentialRecordRepository,
    TokenGateway,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    UpdateUserPasswordResponse,
)
from identity_access_management_context.application.services import (
    REVOCATION_REASON_PASSWORD_CHANGED,
    ExtensionRevocationRecordingService,
)
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import RawPassword
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class UpdateUserPasswordUseCase(TracedUseCase):
    def __init__(
        self,
        password_credential_record_repository: PasswordCredentialRecordRepository,
        password_hashing_gateway: PasswordHashingGateway,
        user_repository: UserRepository,
        auth_session_repository: AuthSessionRepository,
        token_gateway: TokenGateway,
        time_provider: TimeGateway,
        token_credential_record_repository: TokenCredentialRecordRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
    ):
        self.password_credential_record_repository = password_credential_record_repository
        self.password_hashing_gateway = password_hashing_gateway
        self.user_repository = user_repository
        self.auth_session_repository = auth_session_repository
        self.token_gateway = token_gateway
        self.time_provider = time_provider
        self._token_credential_record_repository = token_credential_record_repository
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository

    def execute(self, command: UpdateUserPasswordCommand) -> UpdateUserPasswordResponse:
        credential_records = self.password_credential_record_repository.list_by_principal_id(command.user_id)
        if not credential_records:
            raise UserNotFoundException(command.user_id)

        # A user may hold several passwords: the old one names which to change.
        credential_record = next(
            (
                credential_record
                for credential_record in credential_records
                if self.password_hashing_gateway.verify(command.old_password, credential_record.password_hash)
            ),
            None,
        )
        if credential_record is None:
            raise InvalidCredentialsException("Invalid old password")

        # Checked after the old password so a wrong current password still answers 401
        # rather than leaking policy feedback first.
        new_password = RawPassword(command.new_password)

        user = self.user_repository.get_by_id(command.user_id)
        if not user:
            raise UserNotFoundException(command.user_id)

        new_password_hash = self.password_hashing_gateway.hash(new_password.value)

        self.password_credential_record_repository.update_password_hash(credential_record.email, new_password_hash)

        now = self.time_provider.get_current_time().replace(microsecond=0)

        self.auth_session_repository.invalidate_all_for_principal(user.id, now)

        access_token = self.token_gateway.generate_token(
            principal_id=user.id,
            email=user.email,
            roles=user.roles,
            claims={"display_name": user.name},
        )
        refresh_token = self.token_gateway.generate_refresh_token(
            principal_id=user.id,
            email=user.email,
            roles=user.roles,
        )

        # Keep the current browser session alive while invalidating all previous sessions.
        user.session_invalid_before = now
        self.user_repository.update(user)

        # Extension tokens are revoked outright rather than left to the cutoff
        # above. The cutoff alone did stop them authenticating, but the row kept
        # revoked_at empty, so `is_active` stayed true: the "Connected
        # extensions" screen listed a dead credential as live, and the
        # rate limiter still charged its requests to this user's bucket. Both
        # read the row, not the cutoff.
        revoked = self._token_credential_record_repository.delete_by_principal_ids([user.id])
        if revoked:
            ExtensionRevocationRecordingService.record(
                self._event_publisher,
                self._admin_event_repository,
                user_id=user.id,
                actor_user_id=user.id,
                token_id=None,
                reason=REVOCATION_REASON_PASSWORD_CHANGED,
                revoked_count=revoked,
            )

        if refresh_token.jti is not None:
            self.auth_session_repository.create_session(
                principal_id=user.id,
                refresh_token_jti=refresh_token.jti,
                created_at=now,
            )

        return UpdateUserPasswordResponse(
            access_token=access_token.value,
            refresh_token=refresh_token.value,
        )
