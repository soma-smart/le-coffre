from datetime import datetime
from uuid import uuid4

from identity_access_management_context.application.commands.sso_login_command import (
    SsoLoginCommand,
)
from identity_access_management_context.application.gateways import (
    AuthSessionRepository,
    GroupMemberRepository,
    GroupRepository,
    PasswordHashingGateway,
    SsoConfigurationRepository,
    SSOCredentialRecordRepository,
    SsoEncryptionGateway,
    SsoEventRepository,
    SsoGateway,
    TokenGateway,
    UserRepository,
)
from identity_access_management_context.application.responses.sso_login_response import (
    SsoLoginResponse,
)
from identity_access_management_context.application.services import (
    SsoConfigurationDecryptingService,
    UserCreationService,
    UserManagementService,
)
from identity_access_management_context.application.services.authentication.sso_authenticator import (
    SSOAuthenticator,
)
from identity_access_management_context.domain.entities import SSOCredentialRecord, User
from identity_access_management_context.domain.events import SsoLoginEvent
from identity_access_management_context.domain.value_objects import SSOCredential
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import OrphanedCredentialError, UnknownCredentialError


class SsoLoginUseCase(TracedUseCase):
    """
    Use case for handling SSO login with authorization code.

    This use case orchestrates the SSO login flow:
    1. Validates the SSO code with the provider
    2. Checks if the user already exists in our system
    3. Creates a new user if needed (via User Management context)
    4. Generates a JWT token and creates a session
    """

    def __init__(
        self,
        sso_gateway: SsoGateway,
        sso_authenticator: SSOAuthenticator,
        sso_credential_record_repository: SSOCredentialRecordRepository,
        user_repository: UserRepository,
        auth_session_repository: AuthSessionRepository,
        password_hashing_gateway: PasswordHashingGateway,
        token_gateway: TokenGateway,
        time_provider: TimeGateway,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        sso_configuration_repository: SsoConfigurationRepository,
        sso_encryption_gateway: SsoEncryptionGateway,
        event_publisher: DomainEventPublisher,
        sso_event_repository: SsoEventRepository,
    ):
        self._sso_gateway = sso_gateway
        self._sso_authenticator = sso_authenticator
        self._sso_credential_record_repository = sso_credential_record_repository
        self._user_repository = user_repository
        self._auth_session_repository = auth_session_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._token_gateway = token_gateway
        self._time_provider = time_provider
        self._group_repository = group_repository
        self._group_member_repository = group_member_repository
        self._sso_configuration_repository = sso_configuration_repository
        self._sso_encryption_gateway = sso_encryption_gateway
        self._event_publisher = event_publisher
        self._sso_event_repository = sso_event_repository

    async def execute(self, command: SsoLoginCommand) -> SsoLoginResponse:
        sso_config = SsoConfigurationDecryptingService(
            self._sso_configuration_repository, self._sso_encryption_gateway
        ).decrypt()

        # Step 1: Validate SSO code with the provider — truly async network call.
        sso_user_from_provider = await self._sso_gateway.validate_callback(
            sso_config, command.code, redirect_uri=command.redirect_uri
        )

        # Steps 2-4: All remaining DB reads/writes are synchronous.
        # Called directly (no asyncio.to_thread) because the underlying synchronous
        # repository/session dependencies are not safe to use across threads.
        def _resolve_user():
            credential = SSOCredential(
                provider=sso_user_from_provider.sso_provider, subject=sso_user_from_provider.sso_user_id
            )
            try:
                user = self._sso_authenticator.authenticate(credential)
            except UnknownCredentialError:
                user = None
            except OrphanedCredentialError as error:
                raise RuntimeError("User should exist at this point, but was not found in UserRepository") from error
            if user is not None and not isinstance(user, User):
                # Only users open a session.
                raise RuntimeError("This SSO subject is linked to a principal that is not a user")

            if user is not None:
                is_new_user = False
                self._sso_credential_record_repository.update_last_login(
                    credential.provider, credential.subject, datetime.now()
                )
            else:
                is_new_user = True

                user_management_service = UserManagementService(self._user_repository, self._password_hashing_gateway)
                user = user_management_service.create_user(
                    user_id=uuid4(),
                    email=sso_user_from_provider.email,
                    username=sso_user_from_provider.email.split("@")[0],
                    name=sso_user_from_provider.display_name,
                )
                UserCreationService.create_personal_group_and_set_ownership(
                    user_id=user.id,
                    username=user.username,
                    group_repository=self._group_repository,
                    group_member_repository=self._group_member_repository,
                )
                self._sso_credential_record_repository.create(
                    SSOCredentialRecord(
                        principal_id=user.id,
                        provider=credential.provider,
                        subject=credential.subject,
                        created_at=datetime.now(),
                        last_login=datetime.now(),
                    )
                )

            return user.id, user.email, user.name, is_new_user, user.roles

        user_id, email, display_name, is_new_user, roles = _resolve_user()

        # Step 5: Generate JWT tokens.
        token = self._token_gateway.generate_token(
            principal_id=user_id,
            email=email,
            roles=roles,
            claims={"display_name": display_name},
        )

        refresh_token = self._token_gateway.generate_refresh_token(
            principal_id=user_id,
            email=email,
            roles=roles,
        )
        if refresh_token.jti is not None:
            self._auth_session_repository.create_session(
                principal_id=user_id,
                refresh_token_jti=refresh_token.jti,
                created_at=self._time_provider.get_current_time(),
            )

        event = SsoLoginEvent(user_id=user_id, email=email, is_new_user=is_new_user)
        self._event_publisher.publish(event)
        self._sso_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_principal_id=user_id,
            event_data={"email": email, "is_new_user": is_new_user},
        )

        return SsoLoginResponse(
            jwt_token=token.value,
            refresh_token=refresh_token.value,
            user_id=user_id,
            email=email,
            display_name=display_name,
            is_new_user=is_new_user,
        )
