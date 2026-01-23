#!/usr/bin/env python3
"""
Database migration helper script.

This script provides a convenient way to manage database migrations.
It's a wrapper around Alembic commands.
"""
import sys
import os
from pathlib import Path

# Add src to path so we can import config
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alembic.config import Config
from alembic import command
from config import get_database_url


def main():
    """Run Alembic migration commands."""
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command> [args]")
        print("\nCommon commands:")
        print("  upgrade head     - Apply all pending migrations")
        print("  downgrade -1     - Rollback the last migration")
        print("  current          - Show current migration version")
        print("  history          - Show migration history")
        print("  revision --autogenerate -m 'msg' - Create new migration")
        return 1

    # Configure Alembic with absolute path to alembic.ini
    alembic_ini_path = Path(__file__).parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())

    # Map commands
    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        if cmd == "upgrade":
            revision = args[0] if args else "head"
            command.upgrade(alembic_cfg, revision)
            print(f"✓ Database upgraded to {revision}")
        elif cmd == "downgrade":
            revision = args[0] if args else "-1"
            command.downgrade(alembic_cfg, revision)
            print(f"✓ Database downgraded to {revision}")
        elif cmd == "current":
            command.current(alembic_cfg)
        elif cmd == "history":
            command.history(alembic_cfg)
        elif cmd == "revision":
            # Extract message
            message = None
            autogenerate = False
            i = 0
            while i < len(args):
                if args[i] in ["-m", "--message"] and i + 1 < len(args):
                    message = args[i + 1]
                    i += 2
                elif args[i] == "--autogenerate":
                    autogenerate = True
                    i += 1
                else:
                    i += 1

            if not message:
                print("Error: -m/--message is required for revision command")
                return 1

            command.revision(alembic_cfg, message=message, autogenerate=autogenerate)
            print(f"✓ Created new migration: {message}")
        else:
            print(f"Unknown command: {cmd}")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
