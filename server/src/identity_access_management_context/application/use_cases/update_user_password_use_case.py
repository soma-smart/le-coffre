from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.gateways import (
    AuthSessionRepository,
    PasswordCredentialRecordRepository,
    PasswordHashingGateway,
    TokenGateway,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    UpdateUserPasswordResponse,
)
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import RawPassword
from shared_kernel.application.gateways import TimeGateway
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
    ):
        self.password_credential_record_repository = password_credential_record_repository
        self.password_hashing_gateway = password_hashing_gateway
        self.user_repository = user_repository
        self.auth_session_repository = auth_session_repository
        self.token_gateway = token_gateway
        self.time_provider = time_provider

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
