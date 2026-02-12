from uuid import uuid4
from datetime import datetime

from identity_access_management_context.application.commands.sso_login_command import (
    SsoLoginCommand,
)
from identity_access_management_context.application.responses.sso_login_response import (
    SsoLoginResponse,
)
from identity_access_management_context.application.gateways import (
    SsoGateway,
    SsoUserRepository,
    TokenGateway,
    UserRepository,
    PasswordHashingGateway,
    GroupRepository,
    GroupMemberRepository,
    SsoConfigurationRepository,
    SsoEncryptionGateway,
)
from identity_access_management_context.application.services import (
    UserManagementService,
    UserCreationService,
)
from identity_access_management_context.application.services import (
    SsoConfigurationDecryptingService,
)
from identity_access_management_context.domain.entities.sso_user import SsoUser
from identity_access_management_context.application.gateways import SsoEventRepository
from identity_access_management_context.domain.events import SsoLoginEvent
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway


class SsoLoginUseCase:
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
        sso_user_repository: SsoUserRepository,
        user_repository: UserRepository,
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
        self._sso_user_repository = sso_user_repository
        self._user_repository = user_repository
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
        # Step 0: Retrieve SSO and decrypt secret key
        sso_config = SsoConfigurationDecryptingService(
            self._sso_configuration_repository, self._sso_encryption_gateway
        ).decrypt()

        # Step 1: Validate SSO code and get user info from provider
        sso_user_from_provider = await self._sso_gateway.validate_callback(
            sso_config, command.code
        )

        # Step 2: Check if user already exists in our system
        existing_sso_user = self._sso_user_repository.get_by_sso_user_id(
            sso_user_from_provider.sso_user_id, sso_user_from_provider.sso_provider
        )

        if existing_sso_user:
            # User exists, use existing data
            user_id = existing_sso_user.internal_user_id
            email = existing_sso_user.email
            display_name = existing_sso_user.display_name
            is_new_user = False

            # Update last login time
            self._sso_user_repository.update_last_login(
                sso_user_from_provider.sso_user_id,
                sso_user_from_provider.sso_provider,
                datetime.now(),
            )
        else:
            # Step 3: Create new user
            user_id = uuid4()
            email = sso_user_from_provider.email
            display_name = sso_user_from_provider.display_name
            is_new_user = True

            # Create user in User Management context via service
            user_management_service = UserManagementService(
                self._user_repository, self._password_hashing_gateway
            )
            user = user_management_service.create_user(
                user_id=user_id,
                email=email,
                username=email.split("@")[0],
                name=display_name,
            )

            # Create personal group for the new user
            UserCreationService.create_personal_group_and_set_ownership(
                user_id=user.id,
                username=user.username,
                group_repository=self._group_repository,
                group_member_repository=self._group_member_repository,
            )

            # Save SSO user mapping in Auth context
            sso_user = SsoUser(
                internal_user_id=user_id,
                email=email,
                display_name=display_name,
                sso_user_id=sso_user_from_provider.sso_user_id,
                sso_provider=sso_user_from_provider.sso_provider,
                created_at=datetime.now(),
                last_login=datetime.now(),
            )
            self._sso_user_repository.create(sso_user)

        # Step 4: Generate JWT token
        token = await self._token_gateway.generate_token(
            user_id=user_id,
            email=email,
            roles=["user"],  # SSO users get 'user' role by default
            claims={"display_name": display_name},
        )

        refresh_token = await self._token_gateway.generate_refresh_token(
            user_id=user_id,
            email=email,
            roles=["user"],
        )

        event = SsoLoginEvent(user_id=user_id, email=email, is_new_user=is_new_user)
        self._event_publisher.publish(event)
        self._sso_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=user_id,
            event_data={"email": email, "is_new_user": is_new_user},
        )

        return SsoLoginResponse(
            jwt_token=token.value,
            refresh_token=refresh_token,
            user_id=user_id,
            email=email,
            display_name=display_name,
            is_new_user=is_new_user,
        )
