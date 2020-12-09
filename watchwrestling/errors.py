class IdleUserAPIError(Exception):
    pass


class NoTokenFound(IdleUserAPIError):
    pass


class ValidationError(IdleUserAPIError):
    pass


class InvalidToken(IdleUserAPIError):
    pass


class ResourceNotFoundError(IdleUserAPIError):
    pass


class UserNotRegistered(IdleUserAPIError):
    pass
