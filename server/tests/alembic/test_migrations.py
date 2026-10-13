"""
Tests for Alembic database migrations.

This module tests that migrations can be applied and rolled back successfully.
"""

import importlib
import inspect
import os
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
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
                    # Check if it has table=True (has __tablename__ attribute)
                    if hasattr(obj, "__tablename__"):
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
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='User'"))
        assert result.fetchone() is not None, "User should exist before downgrade"
    engine.dispose()

    # Now downgrade
    command.downgrade(alembic_config, "base")

    # Verify tables are removed (except alembic_version)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='User'"))
        assert result.fetchone() is None, "User should not exist after downgrade"

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
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='User'"))
        assert result.fetchone() is not None
    engine.dispose()

    # Cycle 1: Downgrade
    command.downgrade(alembic_config, "base")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='User'"))
        assert result.fetchone() is None
    engine.dispose()

    # Cycle 2: Upgrade again
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='User'"))
        assert result.fetchone() is not None
    engine.dispose()

    # Cycle 2: Downgrade again
    command.downgrade(alembic_config, "base")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='User'"))
        assert result.fetchone() is None
    engine.dispose()


def _one_time_link_columns(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text('PRAGMA table_info("OneTimeLink")'))}
    engine.dispose()
    return columns


def _one_time_link_indexes(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        indexes = {row[1] for row in conn.execute(text('PRAGMA index_list("OneTimeLink")'))}
    engine.dispose()
    return indexes


def test_one_time_link_notification_migration_defaults_existing_rows_and_downgrades(alembic_config, temp_database):
    """Links created before the migration must come out with both notifications off,
    and the downgrade must drop the new columns while keeping the rows and indexes."""
    database_url, _ = temp_database
    new_columns = {"notify_on_read", "notify_on_expiry", "expiry_notified_at"}

    command.upgrade(alembic_config, "670fae75e21d")
    assert not new_columns & _one_time_link_columns(database_url)
    indexes_before = _one_time_link_indexes(database_url)
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "OneTimeLink" (id, password_id, token_hash, created_by_user_id, created_at, expires_at) '
                "VALUES ('a', 'b', 'hash', 'c', '2026-01-01 00:00:00', '2026-01-02 00:00:00')"
            )
        )
    engine.dispose()

    command.upgrade(alembic_config, "head")

    assert new_columns <= _one_time_link_columns(database_url)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        row = conn.execute(
            text('SELECT notify_on_read, notify_on_expiry, expiry_notified_at FROM "OneTimeLink"')
        ).fetchone()
    engine.dispose()
    assert tuple(row) == (0, 0, None)
    assert _one_time_link_indexes(database_url) == indexes_before

    command.downgrade(alembic_config, "670fae75e21d")

    assert not new_columns & _one_time_link_columns(database_url)
    assert _one_time_link_indexes(database_url) == indexes_before
    engine = create_engine(database_url)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM "OneTimeLink"')).scalar() == 1
    engine.dispose()
