from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from identity_access_management_context.domain.exceptions import (
    InvalidServiceAccountNameError,
)
from shared_kernel.domain.entities.principal import Principal


@dataclass
class ServiceAccount(Principal):
    """A group-owned machine identity.

    Its token is not a field: what proves the account is a separate
    ServiceAccountTokenCredentialRecord, which rotation replaces.

    Rows survive revocation so the group's credential history stays auditable,
    which is why "revoked" is a timestamp rather than a deletion.

    Creation date and creator are deliberately not fields: they are the
    `occurred_on` and `actor_principal_id` of the ServiceAccountCreatedEvent, read
    back when a listing needs them. Revocation is a field, because whether a
    credential is dead must not depend on an audit row still existing.
    """

    _name_length_max: ClassVar[int] = 100
    # Long enough for a descriptive name ("nightly-backup-prod"), short enough that a
    # listing stays readable and that the column cannot be used as free storage.

    group_id: UUID
    name: str
    revoked_at: datetime | None = None

    @classmethod
    def validated_service_account_name(cls, name: str) -> str:
        """Return the name as it should be stored, or raise if it is unusable.

        Exposed separately from create() so a caller checking uniqueness compares
        the same normalised form that will be persisted.
        """
        stripped = name.strip()
        msg = "Service account name "
        if not stripped:
            msg += "cannot be blank"
            raise InvalidServiceAccountNameError(msg)
        if len(stripped) > cls._name_length_max:
            msg += f"must be at most {cls._name_length_max} characters long"
            raise InvalidServiceAccountNameError(msg)
        return stripped

    @classmethod
    def create(cls, group_id: UUID, name: str) -> "ServiceAccount":
        return cls(
            id=uuid4(),
            group_id=group_id,
            name=cls.validated_service_account_name(name),
            revoked_at=None,
        )

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
