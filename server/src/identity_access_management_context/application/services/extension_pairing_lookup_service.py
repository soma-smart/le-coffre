from identity_access_management_context.application.gateways import ExtensionPairingRepository
from identity_access_management_context.domain.entities import ExtensionPairing
from identity_access_management_context.domain.exceptions import ExtensionPairingNotFoundError
from identity_access_management_context.domain.value_objects import PairingUserCode


class ExtensionPairingLookupService:
    """Resolve a user-supplied pairing code to a pairing, or refuse."""

    @staticmethod
    def get_or_raise(repository: ExtensionPairingRepository, raw_user_code: str) -> ExtensionPairing:
        """Find the pairing behind a raw code.

        A malformed code and an unknown code both raise
        ExtensionPairingNotFoundError, so well-formedness cannot be used as a
        probe for which codes exist.

        Args:
            repository: Where pairings are stored.
            raw_user_code: The code as typed or pasted by a human.

        Returns:
            The matching pairing.

        Raises:
            ExtensionPairingNotFoundError: The code is malformed or unknown.
        """
        try:
            user_code = PairingUserCode.parse(raw_user_code)
        except Exception as error:
            raise ExtensionPairingNotFoundError() from error

        pairing = repository.get_by_user_code(user_code)
        if pairing is None:
            raise ExtensionPairingNotFoundError()
        return pairing
