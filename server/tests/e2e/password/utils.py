import jwt


STRONG_PASSWORD = "StrongP@ssw0rd123"


def get_user_id_from_token(token: str) -> str:
    """Extract user_id from JWT token"""
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded["user_id"]
