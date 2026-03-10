import os
import secrets
import warnings


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
        warnings.warn(
            "JWT_SECRET_KEY not set! Using random session key. Set JWT_SECRET_KEY environment variable in production!",
            stacklevel=2,
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


def get_jwt_access_token_expiration_minutes() -> int:
    """Get JWT access token expiration time in minutes. Default is 1 minutes."""
    return int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRATION_MINUTES", "1"))


def get_jwt_refresh_token_expiration_days() -> int:
    """Get JWT refresh token expiration time in days. Default is 7 days."""
    return int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRATION_DAYS", "7"))


def is_production() -> bool:
    """Check if running in production environment."""
    return os.environ.get("ENVIRONMENT", "development") == "production"


def get_cookie_secure_setting() -> bool:
    """
    Get cookie secure setting based on environment.
    In production, cookies should only be sent over HTTPS (secure=True).
    In development/testing, allow HTTP (secure=False).
    """
    return is_production()


# ── Rate Limiting ────────────────────────────────────────────────


def get_rate_limit_enabled() -> bool:
    """Whether rate limiting is enabled. Default is True."""
    return os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"


def get_rate_limit_auth_max_requests() -> int:
    """Max requests per window for authentication routes (login, register, SSO). Default 5."""
    return int(os.environ.get("RATE_LIMIT_AUTH_MAX_REQUESTS", "5"))


def get_rate_limit_api_max_requests() -> int:
    """Max requests per window for general API routes. Default 60."""
    return int(os.environ.get("RATE_LIMIT_API_MAX_REQUESTS", "60"))


def get_rate_limit_window_seconds() -> int:
    """Sliding window duration in seconds. Default 60 (1 minute)."""
    return int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))
