class AuthenticationDomainError(Exception):
    pass


class AdminAlreadyExistsException(AuthenticationDomainError):
    pass


class InvalidCredentialsException(AuthenticationDomainError):
    pass


class AdminNotFoundException(AuthenticationDomainError):
    pass


class InvalidSessionException(AuthenticationDomainError):
    pass


class InvalidTokenException(InvalidSessionException):
    pass


class SessionNotFoundException(InvalidSessionException):
    pass


class UserNotFoundException(InvalidSessionException):
    pass


class InsufficientRoleException(InvalidSessionException):
    pass
