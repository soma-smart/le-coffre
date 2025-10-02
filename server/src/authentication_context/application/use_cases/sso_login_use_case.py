from uuid import uuid4
from datetime import datetime

from authentication_context.application.commands.sso_login_command import (
    SsoLoginCommand,
)
from authentication_context.application.responses.sso_login_response import (
    SsoLoginResponse,
)
from authentication_context.application.gateways import (
    SsoGateway,
    SsoUserRepository,
    UserManagementGateway,
    TokenGateway,
    SessionRepository,
)
from authentication_context.domain.entities.sso_user import SsoUser
from authentication_context.domain.entities.authentication_session import (
    AuthenticationSession,
)


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
        user_management_gateway: UserManagementGateway,
        token_gateway: TokenGateway,
        session_repository: SessionRepository,
    ):
        self._sso_gateway = sso_gateway
        self._sso_user_repository = sso_user_repository
        self._user_management_gateway = user_management_gateway
        self._token_gateway = token_gateway
        self._session_repository = session_repository

    async def execute(self, command: SsoLoginCommand) -> SsoLoginResponse:
        # Step 1: Validate SSO code and get user info from provider
        sso_user_from_provider = await self._sso_gateway.validate_callback(command.code)

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
            existing_sso_user.last_login = datetime.now()
            self._sso_user_repository.save(existing_sso_user)
        else:
            # Step 3: Create new user
            user_id = uuid4()
            email = sso_user_from_provider.email
            display_name = sso_user_from_provider.display_name
            is_new_user = True

            # Create user in User Management context
            await self._user_management_gateway.create_user(
                user_id=user_id, email=email, display_name=display_name
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
            self._sso_user_repository.save(sso_user)

        # Step 4: Generate JWT token
        token = await self._token_gateway.generate_token(
            user_id=user_id,
            email=email,
            roles=["user"],  # SSO users get 'user' role by default
            claims={"display_name": display_name},
        )

        # Step 5: Create session
        session = AuthenticationSession(user_id=user_id, jwt_token=token.value)
        self._session_repository.save(session)

        return SsoLoginResponse(
            jwt_token=token.value,
            user_id=user_id,
            email=email,
            display_name=display_name,
            is_new_user=is_new_user,
        )
