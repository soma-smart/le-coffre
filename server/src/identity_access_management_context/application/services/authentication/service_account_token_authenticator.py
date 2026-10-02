from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.gateways import ServiceAccountRepository
from identity_access_management_context.domain.entities import ServiceAccount
from identity_access_management_context.domain.exceptions import ServiceAccountTokenAuthenticationError
from identity_access_management_context.domain.value_objects import ServiceAccountToken
from shared_kernel.application.authenticator import Authenticator


@dataclass(frozen=True)
class ServiceAccountTokenAuthenticator(Authenticator[ServiceAccountToken]):
    """Resolves a service-account token to the active account holding it.

    A value that does not parse never gets here: building the ServiceAccountToken
    is what rejects it, before any lookup.
    """

    service_account_repository: ServiceAccountRepository

    @override
    def authenticate(self, credential: ServiceAccountToken) -> ServiceAccount:
        """Return the account behind this token.

        Raises:
            ServiceAccountTokenAuthenticationError: if no account holds the token, or the
                one holding it was revoked.
        """
        # The token is 256 bits of randomness, so a lookup by hash alone is safe
        account = self.service_account_repository.get_by_token_hash(credential.hash)
        if account is None or not account.is_active:
            raise ServiceAccountTokenAuthenticationError()
        return account
