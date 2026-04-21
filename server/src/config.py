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


def get_jwt_access_token_expiration_seconds() -> int:
    """Get JWT access token expiration time in seconds. Default is 300 seconds (5 minutes)."""
    return int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRATION_MINUTES", "5")) * 60


def get_jwt_refresh_token_expiration_seconds() -> int:
    """Get JWT refresh token expiration time in seconds. Default is 14400 seconds (4 hours)."""
    return int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRATION_HOURS", "4")) * 3600


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
    """Whether rate limiting is enabled. Default True."""
    return os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"


def get_rate_limit_window_seconds() -> int:
    """Shared sliding-window duration in seconds. Default 60."""
    return int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))


def get_rate_limit_user_max_requests() -> int:
    """Max requests per window for authenticated users (per-user bucket). Default 300."""
    return int(os.environ.get("RATE_LIMIT_USER_MAX_REQUESTS", "300"))


def get_rate_limit_unauth_max_requests() -> int:
    """Max requests per window for unauthenticated callers (per-IP bucket). Default 30."""
    return int(os.environ.get("RATE_LIMIT_UNAUTH_MAX_REQUESTS", "30"))


def get_rate_limit_auth_max_requests() -> int:
    """Max requests per window on credential-accepting auth routes (per-IP floor). Default 100."""
    return int(os.environ.get("RATE_LIMIT_AUTH_MAX_REQUESTS", "100"))


def get_rate_limit_trusted_proxies() -> set[str]:
    """Direct peer IPs whose X-Forwarded-For header is trusted. Default loopback only."""
    raw = os.environ.get("RATE_LIMIT_TRUSTED_PROXIES", "127.0.0.1,::1")
    return {p.strip() for p in raw.split(",") if p.strip()}


def get_rate_limit_trusted_proxy_hops() -> int:
    """Number of trusted proxy hops between client and server (for XFF parsing). Default 1."""
    return int(os.environ.get("RATE_LIMIT_TRUSTED_PROXY_HOPS", "1"))


# ── Login Lockout ────────────────────────────────────────────────


def get_login_max_failed_attempts() -> int:
    """Consecutive failed login attempts before an account is locked. Default 5."""
    return int(os.environ.get("LOGIN_MAX_FAILED_ATTEMPTS", "5"))


def get_login_lockout_seconds() -> int:
    """Duration in seconds an account is locked after hitting the failure threshold. Default 300 (5 min)."""
    return int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "300"))
