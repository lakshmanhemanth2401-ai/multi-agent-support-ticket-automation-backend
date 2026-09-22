class ApplicationError(RuntimeError):
    status_code = 500
    code = "application_error"
    public_message = "The request could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.public_message)


class DependencyUnavailableError(ApplicationError):
    status_code = 503
    code = "dependency_unavailable"
    public_message = "A required service is temporarily unavailable"


class OperationTimeoutError(ApplicationError):
    status_code = 504
    code = "operation_timeout"
    public_message = "The operation timed out"
