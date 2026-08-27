from dataclasses import dataclass

from shared_kernel.domain.exceptions import ReadOnlyCredentialError
from shared_kernel.domain.value_objects import CredentialKind

from .validated_user import ValidatedUser

# Methods an extension credential may use. Everything else is refused before the
# route body runs.
READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class ApiPrincipal:
    """Who is calling, and with how much authority.

    Deliberately a separate type from ValidatedUser rather than extra fields on
    it: ValidatedUser is what ~40 routes already receive, and none of them
    should have to learn about credential kinds to stay correct.
    """

    user: ValidatedUser
    kind: CredentialKind

    @classmethod
    def session(cls, user: ValidatedUser) -> "ApiPrincipal":
        """A cookie-authenticated caller, with the user's own roles."""
        return cls(user=user, kind=CredentialKind.SESSION)

    @classmethod
    def extension(cls, user: ValidatedUser) -> "ApiPrincipal":
        """A browser extension. Read-only, and never admin.

        The caller is expected to have already stripped the roles; this is the
        constructor that documents why.
        """
        return cls(user=user, kind=CredentialKind.EXTENSION)

    @property
    def is_read_only(self) -> bool:
        return self.kind is CredentialKind.EXTENSION

    def ensure_method_allowed(self, method: str) -> None:
        """Refuse a mutating request from a read-only credential.

        Belt to the opt-in allowlist's braces: only three routes declare this
        dependency, all of them GETs, but a future contributor attaching it to a
        POST should not silently widen what an extension token can do.
        """
        if self.is_read_only and method.upper() not in READ_ONLY_METHODS:
            raise ReadOnlyCredentialError(method)
