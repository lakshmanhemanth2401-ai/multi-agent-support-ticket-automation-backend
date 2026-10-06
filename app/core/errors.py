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


class ConflictError(ApplicationError):
    status_code = 409
    code = "invalid_state_transition"
    public_message = "The requested action is not valid for the current state"


class AnalysisInProgressError(ApplicationError):
    status_code = 409
    code = "analysis_in_progress"
    public_message = "AI analysis is already running for this ticket"


class AuthenticationError(ApplicationError):
    status_code = 401
    code = "authentication_required"
    public_message = "Valid authentication credentials are required"
    headers = {"WWW-Authenticate": "Bearer"}


class AuthorizationError(ApplicationError):
    status_code = 403
    code = "permission_denied"
    public_message = "You do not have permission to perform this action"


class SecurityConfigurationError(ApplicationError):
    status_code = 503
    code = "security_not_configured"
    public_message = "Authentication is temporarily unavailable"


class DependencyUnavailableError(ApplicationError):
    status_code = 503
    code = "dependency_unavailable"
    public_message = "A required service is temporarily unavailable"
