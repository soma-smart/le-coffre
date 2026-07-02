"""Validation helpers for browser-opened password URLs."""

from urllib.parse import urlparse


def normalize_optional_http_url(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")

    return normalized
