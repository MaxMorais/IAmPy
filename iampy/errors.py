class BaseError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.name = type(self).__name__
        self.status_code = status_code
    

class ValidationError(BaseError):
    def __init__(self, message):
        super().__init__(417, message)


class NotFoundError(BaseError):
    def __init__(self, message):
        super().__init__(404, message)


class ForbiddenError(BaseError):
    def __init__(self, message):
        super().__init__(403, message)


class DuplicateEntryError(ValidationError):
    pass


class LinkValidationError(ValidationError):
    pass


class MandatoryError(ValidationError):
    pass


class DatabaseError(BaseError):
    def __init__(self, message):
        super().__init__(500, message)


class CannotCommitError(DatabaseError):
    pass


class ValueError(ValidationError):
    pass


class Conflict(ValidationError):
    pass


class InvalidFieldError(ValidationError):
    pass


def throw_error(message, error = None):
    if not error:
        error = 'ValidationError'

    gbl = globals()
    if error in gbl:
        error_class = gbl[error]
    else:
        error_class = ValidationError

    err = error_class(message)
    app.trigger('throw', message=message)
    raise err

