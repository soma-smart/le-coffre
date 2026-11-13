"""add group to service account events

Creation, token rotation and revocation of a service account now show in its
group's history, which filters events on their `group_id`. They also keep the
group's name, so that the audit trail still names a group once it is deleted.
Those events carry both from now on. The ones stored before are given their
`group_id` from the account row, and their `group_name` from the group when it
still exists: the name of a group deleted before cannot be recovered.

Revision ID: d5a8c3f1e7b9
Revises: 9c4e1a7b3d52
Create Date: 2026-11-12 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a8c3f1e7b9'
down_revision: Union[str, Sequence[str], None] = '9c4e1a7b3d52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The events about one account. A listing is scoped to a group already.
ITEM_EVENT_TYPES = (
    'ServiceAccountCreatedEvent',
    'ServiceAccountTokenRotatedEvent',
    'ServiceAccountRevokedEvent',
)


def _in_item_event_types(statement: str) -> sa.TextClause:
    return sa.text(f"{statement} AND event_type IN :event_types").bindparams(
        sa.bindparam('event_types', ITEM_EVENT_TYPES, expanding=True)
    )


def upgrade() -> None:
    """Upgrade schema."""
    # Run by the database, one statement per dialect: setting a JSON key has no
    # portable SQL form. Payloads hold UUIDs in their dashed text form, as
    # `str(UUID)` writes them; SQLite stores the columns as 32 hex digits.
    bind = op.get_bind()
    match bind.dialect.name:
        case 'postgresql':
            op.execute(
                _in_item_event_types(
                    """
                    UPDATE "IamEvent" SET event_data = (
                        event_data::jsonb || jsonb_build_object('group_id', account.group_id::text)
                    )::json
                    FROM iam__principal__service_account AS account
                    WHERE account.principal_id::text = "IamEvent".event_data::jsonb ->> 'service_account_id'
                    AND NOT ("IamEvent".event_data::jsonb ? 'group_id')
                    """
                )
            )
            op.execute(
                _in_item_event_types(
                    """
                    UPDATE "IamEvent" SET event_data = (
                        event_data::jsonb || jsonb_build_object('group_name', "group".name)
                    )::json
                    FROM "Group" AS "group"
                    WHERE "group".id::text = "IamEvent".event_data::jsonb ->> 'group_id'
                    AND NOT ("IamEvent".event_data::jsonb ? 'group_name')
                    """
                )
            )
        case 'sqlite':
            account_of_event = """
                FROM iam__principal__service_account AS account
                WHERE account.principal_id
                    = lower(replace(json_extract("IamEvent".event_data, '$.service_account_id'), '-', ''))
            """
            dashed_group_id = """
                lower(substr(account.group_id, 1, 8) || '-' || substr(account.group_id, 9, 4) || '-'
                || substr(account.group_id, 13, 4) || '-' || substr(account.group_id, 17, 4) || '-'
                || substr(account.group_id, 21, 12))
            """
            op.execute(
                _in_item_event_types(
                    f"""
                    UPDATE "IamEvent" SET event_data = json_set(
                        event_data, '$.group_id', (SELECT {dashed_group_id} {account_of_event})
                    )
                    WHERE json_type(event_data, '$.group_id') IS NULL
                    AND EXISTS (SELECT 1 {account_of_event})
                    """
                )
            )
            group_of_event = """
                FROM "Group" AS grp
                WHERE grp.id = lower(replace(json_extract("IamEvent".event_data, '$.group_id'), '-', ''))
            """
            op.execute(
                _in_item_event_types(
                    f"""
                    UPDATE "IamEvent" SET event_data = json_set(
                        event_data, '$.group_name', (SELECT grp.name {group_of_event})
                    )
                    WHERE json_type(event_data, '$.group_name') IS NULL
                    AND EXISTS (SELECT 1 {group_of_event})
                    """
                )
            )
        case dialect:
            raise NotImplementedError(f"No JSON key update for the {dialect} dialect")


def downgrade() -> None:
    """Downgrade schema.

    Nothing to undo: the code before ignores both keys. Removing them would also
    strip the events written since the upgrade, and lose for good the name of any
    group deleted in between.
    """
