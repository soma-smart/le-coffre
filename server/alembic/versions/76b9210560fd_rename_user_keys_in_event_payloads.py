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
    # Row by row in Python: JSON key renames have no portable SQL form.
    table = sa.table(table_name, sa.column('event_id'), sa.column('event_type'), sa.column('event_data', sa.JSON))
    bind = op.get_bind()
    query = sa.select(table.c.event_id, table.c.event_data)
    if event_types is not None:
        query = query.where(table.c.event_type.in_(event_types))
    for event_id, event_data in bind.execute(query).all():
        if not event_data or not any(old in event_data for old in keys):
            continue
        renamed = {keys.get(key, key): value for key, value in event_data.items()}
        bind.execute(table.update().where(table.c.event_id == event_id).values(event_data=renamed))


def upgrade() -> None:
    """Upgrade schema."""
    _rename_keys('IamEvent', IAM_KEYS, IAM_EVENT_TYPES)
    _rename_keys('PasswordEvent', PASSWORD_KEYS, None)


def downgrade() -> None:
    """Downgrade schema."""
    _rename_keys('PasswordEvent', {new: old for old, new in PASSWORD_KEYS.items()}, None)
    _rename_keys('IamEvent', {new: old for old, new in IAM_KEYS.items()}, IAM_EVENT_TYPES)
