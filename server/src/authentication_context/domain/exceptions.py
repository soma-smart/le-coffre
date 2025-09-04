class AuthenticationDomainError(Exception):
    pass


class InvalidSSOTokenException(AuthenticationDomainError):
    pass


class UnsupportedSSOProviderException(AuthenticationDomainError):
    pass


class AdminAlreadyExistsException(AuthenticationDomainError):
    pass


class InvalidCredentialsException(AuthenticationDomainError):
    pass


class AdminNotFoundException(AuthenticationDomainError):
    pass
