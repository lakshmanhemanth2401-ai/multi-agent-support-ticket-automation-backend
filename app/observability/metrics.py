from prometheus_client import Counter, Histogram

TICKETS_PROCESSED = Counter("support_tickets_processed_total", "Tickets completed by the workflow", ["status"])
AGENT_EXECUTIONS = Counter("support_agent_executions_total", "Agent executions", ["agent", "status"])
AGENT_FAILURES = Counter("support_agent_failures_total", "Agent failures", ["agent", "error_type"])
LLM_REQUESTS = Counter("support_llm_requests_total", "LLM requests", ["operation", "status"])
LLM_LATENCY = Histogram("support_llm_request_duration_seconds", "LLM request latency", ["operation"])
RETRIEVAL_LATENCY = Histogram("support_retrieval_duration_seconds", "Knowledge retrieval latency", ["status"])
WORKFLOW_DURATION = Histogram("support_workflow_duration_seconds", "Workflow duration", ["status"])
REVIEWS = Counter("support_reviews_total", "Review decisions", ["action"])
HTTP_REQUESTS = Counter("support_http_requests_total", "HTTP requests", ["method", "status"])
HTTP_LATENCY = Histogram("support_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
