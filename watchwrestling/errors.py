class IdleUserAPIError(Exception):
    pass


class NoTokenFound(IdleUserAPIError):
    pass


class UserNotRegistered(IdleUserAPIError):
    pass


class BadRequest(IdleUserAPIError):
    pass


class Unauthenticated(IdleUserAPIError):
    pass


class InsufficientPrivileges(IdleUserAPIError):
    pass


class ResourceNotFound(IdleUserAPIError):
    pass


class MethodNotAllowed(IdleUserAPIError):
    pass


class ConflictError(IdleUserAPIError):
    pass


class ValidationError(IdleUserAPIError):
    pass
