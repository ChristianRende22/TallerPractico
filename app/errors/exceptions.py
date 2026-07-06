class AppError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class ValidationError(AppError):
    def __init__(self, message="Validation failed", details=None):
        super().__init__(400, "VALIDATION_ERROR", message, details)


class PostNotFound(AppError):
    def __init__(self, message="Post not found"):
        super().__init__(404, "POST_NOT_FOUND", message)


class InvalidStatusTransition(AppError):
    def __init__(self, message="Invalid status transition"):
        super().__init__(422, "INVALID_STATUS_TRANSITION", message)


class TrashPostLocked(AppError):
    def __init__(self, message="Post in trash cannot be updated"):
        super().__init__(422, "TRASH_POST_LOCKED", message)
