from typing import Any

from app.db.repositories.audit_repository import AuditRepository

_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "authorization", "cookie", "description", "body"}


class AuditService:
    """Persist security-conscious workflow history without ticket content or secrets."""

    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    def record(self, *, ticket_id: int, action: str, details: dict[str, Any] | None = None, commit: bool = True):
        safe = self._sanitize(details or {})
        if commit:
            return self.repository.create(ticket_id=ticket_id, action=action, details=safe)
        return self.repository.add(ticket_id=ticket_id, action=action, details=safe)

    def record_agent_event(self, *, ticket_id: int, agent: str, status: str, details: dict[str, Any] | None = None):
        return self.record(ticket_id=ticket_id, action=f"{agent}_{status}", details=details)

    def record_review_action(self, *, ticket_id: int, action: str, reviewer: str | None):
        return self.record(ticket_id=ticket_id, action=f"review_{action}", details={"reviewer": reviewer})

    def record_workflow_failure(self, *, ticket_id: int, stage: str, error: BaseException):
        return self.record(ticket_id=ticket_id, action="workflow_failed", details={"stage": stage, "error_type": type(error).__name__})

    @classmethod
    def _sanitize(cls, value: Any, key: str = "") -> Any:
        if key.lower() in _SENSITIVE_KEYS or any(word in key.lower() for word in ("password", "secret", "token")):
            return "[REDACTED]"
        if isinstance(value, dict):
            return {str(k): cls._sanitize(v, str(k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._sanitize(item) for item in value]
        if isinstance(value, str):
            return value[:500]
        return value
