class Credential:
    """What a caller presents to prove who it is, secret included.

    It lives for one request and is never stored: what is kept to check it
    against is a `CredentialRecord`, which never holds the secret.
    """
