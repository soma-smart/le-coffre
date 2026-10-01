"""
Tests for Alembic database migrations.

This module tests that migrations can be applied and rolled back successfully.
"""

import importlib
import inspect
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

    command.upgrade(alembic_config, "head")
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
