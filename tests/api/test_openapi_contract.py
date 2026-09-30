from app.main import app


def test_openapi_contains_frontend_contracts_and_bearer_security() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    required = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/tickets",
        "/api/v1/workflows/tickets/{ticket_id}",
        "/api/v1/workflows/{thread_id}",
        "/api/v1/workflows/{thread_id}/review",
        "/api/v1/reviews",
        "/api/v1/tickets/{ticket_id}/audit",
        "/api/v1/knowledge/documents",
        "/api/v1/knowledge/search",
        "/health",
        "/metrics",
    }
    assert required <= set(paths)
    security_schemes = schema["components"]["securitySchemes"]
    assert any(item.get("scheme") == "bearer" for item in security_schemes.values())


def test_workflow_schema_omits_internal_reasoning_and_queries() -> None:
    workflow_schema = app.openapi()["components"]["schemas"]["WorkflowRead"]
    serialized = str(workflow_schema)
    assert "reasoning_summary" not in serialized
    assert '"query"' not in serialized
