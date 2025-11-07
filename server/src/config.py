import os
import secrets


def get_database_url():
    return os.environ.get("DATABASE_URL", "sqlite:///local_db.sqlite")


def get_jwt_secret_key() -> str:
    """
    Get JWT secret key from environment variable.
    
    SECURITY: In production, this MUST be set via environment variable.
    The default is only for development and will raise a warning.
    """
    secret = os.environ.get("JWT_SECRET_KEY")
    
    if not secret:
        # Development fallback - generate a random secret for this session
        # This means tokens won't work across server restarts in dev
        import warnings
        warnings.warn(
            "JWT_SECRET_KEY not set! Using random session key. "
            "Set JWT_SECRET_KEY environment variable in production!",
            UserWarning
        )
        secret = secrets.token_urlsafe(32)
    
    if len(secret) < 32:
        raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
    
    return secret


def get_jwt_algorithm() -> str:
    """Get JWT algorithm. Default is HS256."""
    return os.environ.get("JWT_ALGORITHM", "HS256")


def get_jwt_expiration_hours() -> int:
    """Get JWT expiration time in hours. Default is 24 hours."""
    return int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))
