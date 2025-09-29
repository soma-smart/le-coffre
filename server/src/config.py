import os


def get_database_url():
    return os.environ.get("DATABASE_URL", "sqlite:///local_db.sqlite")
