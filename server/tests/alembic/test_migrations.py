"""
Tests for Alembic database migrations.

This module tests that migrations can be applied and rolled back successfully.
"""
import pytest
import tempfile
import os
import importlib
import inspect
from pathlib import Path
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlmodel import SQLModel


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
            for name, obj in inspect.getmembers(module):
                # Check if it's a class that inherits from SQLModel
                if (inspect.isclass(obj) and 
                    issubclass(obj, SQLModel) and 
                    obj is not SQLModel):
                    # Check if it has table=True (has __tablename__ attribute)
                    if hasattr(obj, '__tablename__'):
                        table_names.append(obj.__tablename__)
        except (ImportError, AttributeError) as e:
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
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ))
        assert result.fetchone() is not None, "alembic_version table should exist"
        
        # Get expected tables dynamically from model __tablename__ attributes
        # This ensures the test stays in sync with model changes
        expected_tables = get_expected_application_tables()
        
        # Verify each expected table exists
        for table_name in expected_tables:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
            ), {"table_name": table_name})
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
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='User'"
        ))
        assert result.fetchone() is not None, "User should exist before downgrade"
    engine.dispose()
    
    # Now downgrade
    command.downgrade(alembic_config, "base")
    
    # Verify tables are removed (except alembic_version)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='User'"
        ))
        assert result.fetchone() is None, "User should not exist after downgrade"
        
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Vault'"
        ))
        assert result.fetchone() is None, "Vault table should not exist after downgrade"
        
        # alembic_version should still exist
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ))
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
    
    assert current_revision == head_revision, \
        f"Database should be at head revision {head_revision}, but is at {current_revision}"


def test_multiple_upgrade_downgrade_cycles(alembic_config, temp_database):
    """Test that migrations can be applied and rolled back multiple times."""
    database_url, db_path = temp_database
    
    # Cycle 1: Upgrade
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='User'"
        ))
        assert result.fetchone() is not None
    engine.dispose()
    
    # Cycle 1: Downgrade
    command.downgrade(alembic_config, "base")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='User'"
        ))
        assert result.fetchone() is None
    engine.dispose()
    
    # Cycle 2: Upgrade again
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='User'"
        ))
        assert result.fetchone() is not None
    engine.dispose()
    
    # Cycle 2: Downgrade again
    command.downgrade(alembic_config, "base")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='User'"
        ))
        assert result.fetchone() is None
    engine.dispose()
