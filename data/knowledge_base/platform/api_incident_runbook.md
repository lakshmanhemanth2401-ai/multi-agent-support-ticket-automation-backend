---
title: Public API Availability Incident Runbook
document_id: SRE-RUN-311
department: Site Reliability Engineering
product: Public API
audience: Support Engineering
version: 4.1
last_reviewed: 2026-08-28
tags: api, outage, latency, incident, rate-limits
---
# Public API Availability Incident Runbook

Use this runbook for elevated API errors, timeouts, unexpected rate limiting, or regional connectivity reports. Start by recording the customer region, endpoint, HTTP method, response status, request ID, first observed time, and whether retries succeed.

## Severity guidance

Declare severity one when the API is unavailable across multiple regions, authentication fails broadly, or confirmed data corruption is occurring. Declare severity two when a major endpoint is degraded for multiple customers or latency exceeds the service objective for fifteen minutes. A single-customer integration issue is normally severity three unless it blocks a critical production workflow without a workaround.

## Investigation

Check gateway request rate, server error percentage, latency percentiles, database saturation, queue depth, and active deployments. Compare affected and unaffected regions. For HTTP 429 responses, verify both the documented account limit and the returned rate-limit headers before assuming a platform defect. Do not advise customers to create additional accounts to bypass limits.

If a recent deployment correlates with the failure, the incident commander decides whether to roll back. Support must not promise a rollback or recovery time until Engineering confirms it. Provide customer updates at the incident's defined communication interval and distinguish confirmed facts from investigation hypotheses.

## Customer-safe evidence

Request minimal reproducible examples with secrets removed. API keys, bearer tokens, signed URLs, customer payload data, and personal information must be redacted. Request IDs are safe to share and are the preferred method for locating server-side traces.

Close the incident only after health metrics recover, synthetic checks pass, and the incident commander confirms stability. Link affected support tickets to the incident record for later follow-up.
