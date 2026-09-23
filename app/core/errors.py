class ApplicationError(RuntimeError):
    status_code = 500
    code = "application_error"
    public_message = "The request could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.public_message)


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    code = "resource_not_found"
    public_message = "The requested resource was not found"
