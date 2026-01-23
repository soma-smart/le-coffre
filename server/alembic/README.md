# Database Migrations

This directory contains Alembic database migrations for Le Coffre.

## Overview

Le Coffre uses [Alembic](https://alembic.sqlalchemy.org/) to manage database schema changes. Migrations are version-controlled and allow you to:
- Track schema changes over time
- Apply schema changes to databases
- Roll back to previous schema versions
- Ensure consistent database state across environments

## Directory Structure

```
alembic/
├── versions/          # Migration scripts
├── env.py            # Alembic environment configuration
├── script.py.mako    # Template for new migrations
└── README.md         # This file
```

## Common Commands

### Using the helper script (recommended)
```bash
cd server

# Check current migration version
python migrate.py current

# Apply all pending migrations
python migrate.py upgrade head

# Rollback one migration
python migrate.py downgrade -1

# View migration history
python migrate.py history

# Create a new migration
python migrate.py revision --autogenerate -m "Description of changes"
```

### Using Alembic directly
```bash
cd server

# Check current migration version
alembic current

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history --verbose

# Create a new migration
alembic revision --autogenerate -m "Description of changes"
```

**Important:** Always review the auto-generated migration before applying it. Alembic may not detect all changes correctly.

## How Migrations Work

1. **Automatic on Startup**: The application automatically runs `alembic upgrade head` on startup via the `run_migrations()` function in `main.py`.

2. **SQLModel Integration**: The `alembic/env.py` file imports all SQLModel table definitions and uses `SQLModel.metadata` to detect schema changes.

3. **Database URL**: The database URL is read from the `DATABASE_URL` environment variable (or defaults to `sqlite:///local_db.sqlite` for development).

## Creating Migrations

When you add or modify a SQLModel table:

1. Make your changes to the model files in `src/*/adapters/secondary/sql/model/`
2. Create a migration:
   ```bash
   cd server
   python migrate.py revision --autogenerate -m "Add new_column to UserTable"
   # or use alembic directly:
   # alembic revision --autogenerate -m "Add new_column to UserTable"
   ```
3. Review the generated file in `alembic/versions/`
4. Test the migration:
   ```bash
   python migrate.py upgrade head  # Apply
   python migrate.py downgrade -1  # Rollback
   python migrate.py upgrade head  # Re-apply
   ```
5. Commit the migration file to version control

## Migration Best Practices

- **Always review auto-generated migrations** - Alembic may miss some changes
- **Test rollback** - Ensure `downgrade()` works correctly
- **Keep migrations small** - One logical change per migration
- **Never edit applied migrations** - Create a new migration instead
- **Add data migrations carefully** - Use `op.execute()` for data changes

## Troubleshooting

### "FAILED: Target database is not up to date"
This means your database is behind the latest migration. Run:
```bash
alembic upgrade head
```

### "Can't locate revision identified by '...'"
Your `alembic_version` table may be out of sync. Check:
```bash
alembic current
alembic history
```

### Migration conflicts
If you have multiple feature branches with migrations, you may need to merge them:
```bash
alembic merge <rev1> <rev2> -m "Merge migrations"
```

## Reference

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Migration Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
