from dataclasses import dataclass

from ._response import ServiceAccountItemResponse


@dataclass(frozen=True, kw_only=True)
class RevokeServiceAccountResponse(ServiceAccountItemResponse):
    """Response on service account revocation."""
