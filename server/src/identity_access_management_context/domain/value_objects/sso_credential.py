from dataclasses import dataclass

from shared_kernel.domain.value_objects.credential import Credential


@dataclass(frozen=True)
class SSOCredential(Credential):
    """The subject an SSO provider vouched for, once the OIDC code exchange succeeded."""

    provider: str
    subject: str
