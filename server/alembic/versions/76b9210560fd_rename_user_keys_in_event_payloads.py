"""rename user keys in event payloads

Stored event payloads name a principal the same way their columns now do:
the member of a membership event, the actor of a service-account event, and
the actor and issuer of password events. Payloads whose subject is a user by
construction (user created, updated, deleted, promoted) keep `user_id`.

Revision ID: 76b9210560fd
Revises: 83cc85f63482
Create Date: 2026-10-02 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76b9210560fd'
down_revision: Union[str, Sequence[str], None] = '83cc85f63482'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# IamEvent payloads carrying a principal under `user_id`, by event type.
IAM_EVENT_TYPES = (
    'UserAddedToGroupEvent',
    'OwnerAddedToGroupEvent',
    'UserRemovedFromGroupEvent',
    'OwnerDemotedToMemberEvent',
    'ServiceAccountCreatedEvent',
    'ServiceAccountTokenRotatedEvent',
    'ServiceAccountRevokedEvent',
    'ServiceAccountsListedEvent',
)
IAM_KEYS = {'user_id': 'principal_id'}
# PasswordEvent payloads: these keys only ever hold a principal, whatever the event.
PASSWORD_KEYS = {'by_user_id': 'by_principal_id', 'issued_by_user_id': 'issued_by_principal_id'}


def _rename_keys(table_name: str, keys: dict[str, str], event_types: tuple[str, ...] | None) -> None:
    # One statement per key, run by the database: the payloads never go through
    # Python. Renaming a JSON key has no portable SQL form, hence one per dialect.
    bind = op.get_bind()
    for old, new in keys.items():
        match bind.dialect.name:
            case 'postgresql':
                renamed = f"((event_data::jsonb - '{old}') || jsonb_build_object('{new}', event_data::jsonb -> '{old}'))::json"
                holds_key = f"event_data::jsonb ? '{old}'"
            case 'sqlite':
                renamed = f"json_set(json_remove(event_data, '$.{old}'), '$.{new}', json_extract(event_data, '$.{old}'))"
                holds_key = f"json_type(event_data, '$.{old}') IS NOT NULL"
            case dialect:
                raise NotImplementedError(f"No JSON key rename for the {dialect} dialect")
        statement = f'UPDATE "{table_name}" SET event_data = {renamed} WHERE {holds_key}'
        if event_types is None:
            op.execute(sa.text(statement))
        else:
            op.execute(
                sa.text(f"{statement} AND event_type IN :event_types").bindparams(
                    sa.bindparam('event_types', event_types, expanding=True)
                )
            )


def upgrade() -> None:
    """Upgrade schema."""
    _rename_keys('IamEvent', IAM_KEYS, IAM_EVENT_TYPES)
    _rename_keys('PasswordEvent', PASSWORD_KEYS, None)


def downgrade() -> None:
    """Downgrade schema."""
    _rename_keys('PasswordEvent', {new: old for old, new in PASSWORD_KEYS.items()}, None)
    _rename_keys('IamEvent', {new: old for old, new in IAM_KEYS.items()}, IAM_EVENT_TYPES)
