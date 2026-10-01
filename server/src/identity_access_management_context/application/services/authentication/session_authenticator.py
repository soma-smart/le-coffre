from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.commands import ValidateUserTokenCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.use_cases.validate_user_token_use_case import (
    ValidateUserTokenUseCase,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    SessionAuthenticationError,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import SessionToken
from shared_kernel.application.authenticator import Authenticator


@dataclass(frozen=True)
class SessionAuthenticator(Authenticator[SessionToken]):
    """Resolves the session a login issued to the user it belongs to.

    The session checks stay in ValidateUserTokenUseCase, which get_current_user
    still calls directly: delegating to it keeps one definition of a valid
    session, rather than two that could drift apart.
    """

    validate_user_token_use_case: ValidateUserTokenUseCase
    user_repository: UserRepository

    @override
    def authenticate(self, authentication: SessionToken) -> User:
        """Return the user this session belongs to.

        Raises:
            SessionAuthenticationError: if the session is not valid, or its user
                no longer exists.
        """
        try:
            validated = self.validate_user_token_use_case.execute(
                ValidateUserTokenCommand(jwt_token=authentication.value)
            )
        except (InvalidTokenException, UserNotFoundException) as error:
            raise SessionAuthenticationError() from error

        user = self.user_repository.get_by_id(validated.user_id)
        if user is None:
            raise SessionAuthenticationError()
        return user
