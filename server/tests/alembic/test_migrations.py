"""
Tests for Alembic database migrations.

This module tests that migrations can be applied and rolled back successfully.
"""

import importlib
import inspect
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel

from alembic import command


def get_expected_application_tables():
    """
    Dynamically discover all SQLModel table classes from the application.

    This function scans all adapters/secondary/sql/__init__.py files in the src directory,
    imports them, and extracts all classes that inherit from SQLModel and have table=True.
    This ensures the test automatically stays in sync with model changes.
    """
    # Get the src directory path
    src_dir = Path(__file__).parent.parent.parent / "src"

    # Find all sql __init__.py files
    sql_init_files = list(src_dir.glob("**/adapters/secondary/sql/__init__.py"))

    table_names = []

    for init_file in sql_init_files:
        # Build module path relative to src directory
        relative_path = init_file.relative_to(src_dir)
        module_parts = list(relative_path.parts[:-1])  # Remove __init__.py
        module_name = ".".join(module_parts)

        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Inspect all members of the module
            for _, obj in inspect.getmembers(module):
                # Check if it's a class that inherits from SQLModel
                if inspect.isclass(obj) and issubclass(obj, SQLModel) and obj is not SQLModel:
                    # Only table=True classes are mapped; every SQLModel has a __tablename__
                    if hasattr(obj, "__table__"):
                        table_names.append(obj.__tablename__)
        except (ImportError, AttributeError):
            # Some modules might not be importable or might not have tables
            # This is expected (e.g., shared_kernel has no tables)
            continue

    return sorted(set(table_names))  # Return unique sorted list


@pytest.fixture
def temp_database():
    """Create a temporary SQLite database for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    database_url = f"sqlite:///{db_path}"

    yield database_url, db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def alembic_config(temp_database):
    """Create an Alembic config for testing."""
    database_url, _ = temp_database

    # Get the path to alembic.ini
    alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

    config = Config(str(alembic_ini_path))
    config.set_main_option("sqlalchemy.url", database_url)

    return config


def test_upgrade_migration_creates_all_tables(alembic_config, temp_database):
    """Test that running 'upgrade head' creates all expected tables."""
    database_url, db_path = temp_database

    # Run migrations
    command.upgrade(alembic_config, "head")

    # Verify tables were created
    engine = create_engine(database_url)
    with engine.connect() as conn:
        # Check for alembic version table
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"))
        assert result.fetchone() is not None, "alembic_version table should exist"

        # Get expected tables dynamically from model __tablename__ attributes
        # This ensures the test stays in sync with model changes
        expected_tables = get_expected_application_tables()

        # Verify each expected table exists
        for table_name in expected_tables:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
                {"table_name": table_name},
            )
            assert result.fetchone() is not None, f"Table {table_name} should exist after migration"

    engine.dispose()


def test_downgrade_migration_removes_tables(alembic_config, temp_database):
    """Test that running 'downgrade' removes all tables."""
    database_url, db_path = temp_database

    # First upgrade to head
    command.upgrade(alembic_config, "head")

    # Verify tables exist
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='iam__principal'"))
        assert result.fetchone() is not None, "iam__principal should exist before downgrade"
    engine.dispose()

    # Now downgrade
    command.downgrade(alembic_config, "base")

    # Verify tables are removed (except alembic_version)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='iam__principal'"))
        assert result.fetchone() is None, "iam__principal should not exist after downgrade"

        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='Vault'"))
        assert result.fetchone() is None, "Vault table should not exist after downgrade"

        # alembic_version should still exist
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"))
        assert result.fetchone() is not None, "alembic_version table should still exist"

    engine.dispose()


def test_migration_is_at_head_after_upgrade(alembic_config, temp_database):
    """Test that after upgrade, the database is at the head revision."""
    database_url, db_path = temp_database

    # Run migrations
    command.upgrade(alembic_config, "head")

    # Get the current revision
    script = ScriptDirectory.from_config(alembic_config)
    head_revision = script.get_current_head()

    # Check database revision
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_revision = result.fetchone()[0]
    engine.dispose()

    assert current_revision == head_revision, (
        f"Database should be at head revision {head_revision}, but is at {current_revision}"
    )


def test_multiple_upgrade_downgrade_cycles(alembic_config, temp_database):
    """Test that migrations can be applied and rolled back multiple times."""
    database_url, db_path = temp_database

    # Cycle 1: Upgrade
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='iam__principal'"))
        assert result.fetchone() is not None
    engine.dispose()

    # Cycle 1: Downgrade
    command.downgrade(alembic_config, "base")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='iam__principal'"))
        assert result.fetchone() is None
    engine.dispose()

    # Cycle 2: Upgrade again
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='iam__principal'"))
        assert result.fetchone() is not None
    engine.dispose()

    # Cycle 2: Downgrade again
    command.downgrade(alembic_config, "base")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='iam__principal'"))
        assert result.fetchone() is None
    engine.dispose()


PRE_PRINCIPAL_REVISION = "6f3f296a75c9"
"""Last revision where users and service accounts had their own tables."""

PRINCIPAL_REVISION = "b2756d236d95"
"""Revision adding the principal registry, before credentials had their own tables."""

CREDENTIALS_REVISION = "c2fe6004a6d0"
"""Revision moving credentials to their own tables, while revoked accounts still kept their token."""

REVOKED_TOKENS_REVISION = "528c0676a893"
"""Revision deleting the token credentials of revoked service accounts."""


def test_principal_registry_migration_keeps_every_id_with_its_kind(alembic_config, temp_database):
    """Users and service accounts survive the move, under the same ids, and come back on downgrade."""
    database_url, _ = temp_database
    user_id, account_id, group_id = uuid4(), uuid4(), uuid4()

    command.upgrade(alembic_config, PRE_PRINCIPAL_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "User" (id, username, email, name, roles, current_refresh_token_jti) '
                "VALUES (:id, 'alice', 'alice@example.com', 'Alice', '[\"admin\"]', 'jti-1')"
            ),
            {"id": user_id.hex},
        )
        conn.execute(
            text(
                'INSERT INTO "ServiceAccount" (id, group_id, name, token_hash) '
                "VALUES (:id, :group_id, 'nightly-backup', 'hash-1')"
            ),
            {"id": account_id.hex, "group_id": group_id.hex},
        )
    engine.dispose()

    command.upgrade(alembic_config, PRINCIPAL_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        kinds = dict(conn.execute(text("SELECT id, kind FROM iam__principal")).all())
        user = conn.execute(
            text("SELECT username, email, name, roles, current_refresh_token_jti FROM iam__principal__user")
        ).one()
        account = conn.execute(
            text("SELECT principal_id, group_id, name, token_hash FROM iam__principal__service_account")
        ).one()
    engine.dispose()

    assert kinds == {user_id.hex: "user", account_id.hex: "service_account"}
    assert tuple(user) == ("alice", "alice@example.com", "Alice", '["admin"]', "jti-1")
    assert tuple(account) == (account_id.hex, group_id.hex, "nightly-backup", "hash-1")

    command.downgrade(alembic_config, PRE_PRINCIPAL_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT id, username FROM "User"')).all() == [(user_id.hex, "alice")]
        assert conn.execute(text('SELECT id, token_hash FROM "ServiceAccount"')).all() == [(account_id.hex, "hash-1")]
    engine.dispose()


def test_credentials_migration_moves_every_verifier_to_its_principal(alembic_config, temp_database):
    """Passwords, SSO subjects and token hashes move to credential tables and come back on downgrade."""
    database_url, _ = temp_database
    user_id, sso_user_id, orphan_id, account_id = uuid4(), uuid4(), uuid4(), uuid4()

    command.upgrade(alembic_config, PRINCIPAL_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as conn:
        for principal_id, kind in ((user_id, "user"), (sso_user_id, "user"), (account_id, "service_account")):
            conn.execute(
                text("INSERT INTO iam__principal (id, kind) VALUES (:id, :kind)"),
                {"id": principal_id.hex, "kind": kind},
            )
        for principal_id, username in ((user_id, "alice"), (sso_user_id, "bob")):
            conn.execute(
                text(
                    "INSERT INTO iam__principal__user (principal_id, username, email, name, roles) "
                    "VALUES (:id, :username, :email, :name, '[]')"
                ),
                {"id": principal_id.hex, "username": username, "email": f"{username}@new.example", "name": username},
            )
        conn.execute(
            text(
                "INSERT INTO iam__principal__service_account (principal_id, group_id, name, token_hash) "
                "VALUES (:id, :group_id, 'nightly-backup', 'hash-1')"
            ),
            {"id": account_id.hex, "group_id": uuid4().hex},
        )
        # The copies drifted from the user: the login email must survive, the display name must not.
        for principal_id, email in ((user_id, "alice@old.example"), (orphan_id, "gone@example.com")):
            conn.execute(
                text(
                    'INSERT INTO "UserPassword" (id, email, password_hash, display_name) '
                    "VALUES (:id, :email, :hash, 'Stale Name')"
                ),
                {"id": principal_id.hex, "email": email, "hash": b"bcrypt-hash"},
            )
        conn.execute(
            text(
                'INSERT INTO "SsoUser" (internal_user_id, email, display_name, sso_user_id, sso_provider) '
                "VALUES (:id, 'bob@old.example', 'Stale Name', 'subject-1', 'google')"
            ),
            {"id": sso_user_id.hex},
        )
    engine.dispose()

    command.upgrade(alembic_config, CREDENTIALS_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as conn:

        def credentials(kind: str, columns: str) -> list:
            return conn.execute(
                text(
                    f"SELECT c.principal_id, {columns} FROM iam__credential c "
                    f"JOIN iam__credential__{kind} d ON d.credential_id = c.id WHERE c.kind = :kind"
                ),
                {"kind": kind},
            ).all()

        passwords = credentials("password", "d.email, d.password_hash")
        sso = credentials("sso", "d.provider, d.subject")
        tokens = credentials("token", "d.token_hash")
        registered = conn.execute(text("SELECT count(*) FROM iam__credential")).scalar_one()
        account_columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(iam__principal__service_account)")).all()
        }
    engine.dispose()

    # The orphaned password is left behind: it pointed to no principal.
    assert passwords == [(user_id.hex, "alice@old.example", b"bcrypt-hash")]
    assert sso == [(sso_user_id.hex, "google", "subject-1")]
    assert tokens == [(account_id.hex, "hash-1")]
    assert registered == 3
    assert "token_hash" not in account_columns

    command.downgrade(alembic_config, PRINCIPAL_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT id, email, display_name FROM "UserPassword"')).all() == [
            (user_id.hex, "alice@old.example", "alice")
        ]
        assert conn.execute(text('SELECT internal_user_id, email, display_name, sso_user_id FROM "SsoUser"')).all() == [
            (sso_user_id.hex, "bob@new.example", "bob", "subject-1")
        ]
        assert conn.execute(text("SELECT principal_id, token_hash FROM iam__principal__service_account")).all() == [
            (account_id.hex, "hash-1")
        ]
    engine.dispose()


def test_revoked_tokens_migration_deletes_only_revoked_accounts_tokens(alembic_config, temp_database):
    """A revoked account loses its token credential; an active one keeps it."""
    database_url, _ = temp_database
    active_id, revoked_id = uuid4(), uuid4()

    command.upgrade(alembic_config, CREDENTIALS_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as conn:
        for principal_id, revoked_at in ((active_id, None), (revoked_id, "2026-01-01 12:00:00")):
            credential_id = uuid4()
            conn.execute(
                text("INSERT INTO iam__principal (id, kind) VALUES (:id, 'service_account')"), {"id": principal_id.hex}
            )
            conn.execute(
                text(
                    "INSERT INTO iam__principal__service_account (principal_id, group_id, name, revoked_at) "
                    "VALUES (:id, :group_id, 'nightly-backup', :revoked_at)"
                ),
                {"id": principal_id.hex, "group_id": uuid4().hex, "revoked_at": revoked_at},
            )
            conn.execute(
                text("INSERT INTO iam__credential (id, kind, principal_id) VALUES (:id, 'token', :principal_id)"),
                {"id": credential_id.hex, "principal_id": principal_id.hex},
            )
            conn.execute(
                text("INSERT INTO iam__credential__token (credential_id, token_hash) VALUES (:id, :hash)"),
                {"id": credential_id.hex, "hash": f"hash-{principal_id.hex}"},
            )
    engine.dispose()

    command.upgrade(alembic_config, REVOKED_TOKENS_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        registered = conn.execute(text("SELECT principal_id FROM iam__credential")).scalars().all()
        hashes = conn.execute(text("SELECT token_hash FROM iam__credential__token")).scalars().all()
    engine.dispose()

    assert registered == [active_id.hex]
    assert hashes == [f"hash-{active_id.hex}"]


def test_deleting_a_principal_deletes_its_credentials(alembic_config, temp_database):
    """The foreign keys cascade from the principal to its registry rows, then to their details."""
    database_url, _ = temp_database
    principal_id, credential_id = uuid4(), uuid4()
    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    with engine.begin() as conn:
        # SQLite enforces foreign keys, and so runs the cascade, only when asked to.
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.execute(text("INSERT INTO iam__principal (id, kind) VALUES (:id, 'user')"), {"id": principal_id.hex})
        conn.execute(
            text("INSERT INTO iam__credential (id, kind, principal_id) VALUES (:id, 'password', :principal_id)"),
            {"id": credential_id.hex, "principal_id": principal_id.hex},
        )
        conn.execute(
            text(
                "INSERT INTO iam__credential__password (credential_id, email, password_hash) "
                "VALUES (:id, 'alice@example.com', :hash)"
            ),
            {"id": credential_id.hex, "hash": b"bcrypt-hash"},
        )

        conn.execute(text("DELETE FROM iam__principal WHERE id = :id"), {"id": principal_id.hex})

        assert conn.execute(text("SELECT count(*) FROM iam__credential")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM iam__credential__password")).scalar_one() == 0
    engine.dispose()


def test_principal_kind_column_accepts_exactly_the_enum_values(alembic_config, temp_database):
    """Adding a PrincipalKind without a migration extending the CHECK constraint fails here."""
    from identity_access_management_context.adapters.secondary.sql import PrincipalKind

    database_url, _ = temp_database
    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    with engine.begin() as conn:
        for kind in PrincipalKind:
            conn.execute(
                text("INSERT INTO iam__principal (id, kind) VALUES (:id, :kind)"),
                {"id": uuid4().hex, "kind": kind.value},
            )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("INSERT INTO iam__principal (id, kind) VALUES (:id, 'robot')"), {"id": uuid4().hex})
    engine.dispose()


def test_a_principal_may_hold_several_credentials_of_one_kind(alembic_config, temp_database):
    """Credentials of a kind are not limited to one per principal."""
    database_url, _ = temp_database
    command.upgrade(alembic_config, "head")
    principal_id = uuid4()

    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO iam__principal (id, kind) VALUES (:id, 'user')"), {"id": principal_id.hex})
        for _ in range(2):
            conn.execute(
                text("INSERT INTO iam__credential (id, kind, principal_id) VALUES (:id, 'password', :principal_id)"),
                {"id": uuid4().hex, "principal_id": principal_id.hex},
            )
        registered = conn.execute(
            text("SELECT count(*) FROM iam__credential WHERE principal_id = :id"), {"id": principal_id.hex}
        ).scalar_one()
    engine.dispose()

    assert registered == 2


PRINCIPAL_COLUMNS_REVISION = "83cc85f63482"
"""Revision renaming the user columns that hold any principal."""


def test_principal_columns_migration_keeps_every_value(alembic_config, temp_database):
    """Renamed columns keep their values, and get their old names back on downgrade."""
    database_url, _ = temp_database
    principal_id, group_id = uuid4().hex, uuid4().hex
    rows = {
        "Group": ("id, name, is_personal, user_id", f"'{group_id}', 'Personal', 1, '{principal_id}'"),
        "GroupMember": ("group_id, user_id, is_owner", f"'{group_id}', '{principal_id}', 1"),
        "AuthSession": (
            "id, user_id, current_refresh_token_jti, created_at, updated_at",
            f"'{uuid4().hex}', '{principal_id}', 'jti-1', '2026-01-01 12:00:00', '2026-01-01 12:00:00'",
        ),
        "RevokedToken": (
            "id, jti, user_id, token_type, revoked_at, reason",
            f"'{uuid4().hex}', 'jti-2', '{principal_id}', 'refresh', '2026-01-01 12:00:00', 'logout'",
        ),
        "IamEvent": (
            "event_id, event_type, occurred_on, actor_user_id, event_data",
            f"'{uuid4().hex}', 'GroupCreatedEvent', '2026-01-01 12:00:00', '{principal_id}', '{{}}'",
        ),
        "PasswordEvent": (
            "event_id, event_type, occurred_on, password_id, actor_user_id, event_data",
            f"'{uuid4().hex}', 'PasswordCreatedEvent', '2026-01-01 12:00:00', '{uuid4().hex}', '{principal_id}', '{{}}'",
        ),
        "VaultEvent": (
            "event_id, event_type, occurred_on, actor_user_id, event_data",
            f"'{uuid4().hex}', 'VaultLockedEvent', '2026-01-01 12:00:00', '{principal_id}', '{{}}'",
        ),
        "OneTimeLink": (
            "id, password_id, token_hash, created_by_user_id, created_at, expires_at",
            f"'{uuid4().hex}', '{uuid4().hex}', 'hash-1', '{principal_id}', '2026-01-01 12:00:00', '2026-01-02 12:00:00'",
        ),
    }
    renamed = {
        "Group": "principal_id",
        "GroupMember": "principal_id",
        "AuthSession": "principal_id",
        "RevokedToken": "principal_id",
        "IamEvent": "actor_principal_id",
        "PasswordEvent": "actor_principal_id",
        "OneTimeLink": "created_by_principal_id",
        "VaultEvent": "actor_principal_id",
    }

    command.upgrade(alembic_config, REVOKED_TOKENS_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as conn:
        for table, (columns, values) in rows.items():
            conn.execute(text(f'INSERT INTO "{table}" ({columns}) VALUES ({values})'))
    engine.dispose()

    command.upgrade(alembic_config, PRINCIPAL_COLUMNS_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        upgraded = {
            table: conn.execute(text(f'SELECT {column} FROM "{table}"')).scalar_one()
            for table, column in renamed.items()
        }
    engine.dispose()

    command.downgrade(alembic_config, REVOKED_TOKENS_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        downgraded = {
            table: conn.execute(text(f'SELECT {column.replace("principal", "user")} FROM "{table}"')).scalar_one()
            for table, column in renamed.items()
        }
    engine.dispose()

    assert upgraded == dict.fromkeys(renamed, principal_id)
    assert downgraded == dict.fromkeys(renamed, principal_id)


PAYLOAD_KEYS_REVISION = "76b9210560fd"
"""Revision renaming the user keys that hold any principal in stored event payloads."""


def test_payload_keys_migration_renames_only_principal_keys(alembic_config, temp_database):
    """Principal keys are renamed and come back on downgrade; a user-only payload keeps user_id."""
    database_url, _ = temp_database
    principal_id = uuid4().hex
    iam_events = {
        "UserAddedToGroupEvent": {"group_id": "g-1", "user_id": principal_id},
        "ServiceAccountCreatedEvent": {"user_id": principal_id, "service_account_id": "sa-1"},
        "UserCreatedEvent": {"user_id": principal_id, "username": "alice"},
    }
    password_event = {"password_id": "p-1", "by_user_id": principal_id, "issued_by_user_id": principal_id}

    command.upgrade(alembic_config, PRINCIPAL_COLUMNS_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as conn:
        for event_type, data in iam_events.items():
            conn.execute(
                text(
                    'INSERT INTO "IamEvent" (event_id, event_type, occurred_on, event_data) '
                    "VALUES (:id, :type, '2026-01-01 12:00:00', :data)"
                ),
                {"id": uuid4().hex, "type": event_type, "data": json.dumps(data)},
            )
        conn.execute(
            text(
                'INSERT INTO "PasswordEvent" (event_id, event_type, occurred_on, password_id, actor_principal_id, event_data) '
                "VALUES (:id, 'OneTimeLinkRevokedEvent', '2026-01-01 12:00:00', :password_id, :actor, :data)"
            ),
            {"id": uuid4().hex, "password_id": uuid4().hex, "actor": principal_id, "data": json.dumps(password_event)},
        )
    engine.dispose()

    def payloads() -> tuple[dict, dict]:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            iam = {
                t: json.loads(d) for t, d in conn.execute(text('SELECT event_type, event_data FROM "IamEvent"')).all()
            }
            password = json.loads(conn.execute(text('SELECT event_data FROM "PasswordEvent"')).scalar_one())
        engine.dispose()
        return iam, password

    command.upgrade(alembic_config, PAYLOAD_KEYS_REVISION)
    iam, password = payloads()
    assert iam["UserAddedToGroupEvent"] == {"group_id": "g-1", "principal_id": principal_id}
    assert iam["ServiceAccountCreatedEvent"] == {"principal_id": principal_id, "service_account_id": "sa-1"}
    assert iam["UserCreatedEvent"] == {"user_id": principal_id, "username": "alice"}
    assert password == {"password_id": "p-1", "by_principal_id": principal_id, "issued_by_principal_id": principal_id}

    command.downgrade(alembic_config, PRINCIPAL_COLUMNS_REVISION)
    iam, password = payloads()
    assert iam == iam_events
    assert password == password_event
