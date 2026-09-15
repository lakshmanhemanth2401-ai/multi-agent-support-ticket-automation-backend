---
title: Enterprise SSO Access Troubleshooting Runbook
document_id: IAM-RUN-104
department: Identity and Access Management
product: Enterprise Portal
audience: Support Engineering
version: 3.2
last_reviewed: 2026-08-14
tags: sso, saml, login, identity, access
---
# Enterprise SSO Access Troubleshooting Runbook

Use this runbook when an employee or customer cannot authenticate through an organization-managed SAML or OIDC identity provider. Never ask a user to send a password, recovery code, session cookie, private key, or complete authentication assertion.

## Initial triage

Confirm whether the problem affects one user, one tenant, or multiple tenants. Record the tenant identifier, identity provider, approximate failure time with timezone, browser, correlation ID, and the exact user-visible error. Check the status page before changing configuration. If multiple tenants are affected or authentication is broadly unavailable, open a severity-one incident and notify the identity on-call engineer.

For one affected user, confirm that the account is active, assigned to the application, and using an email address or immutable subject identifier that matches the tenant mapping. Ask the user to retry in a private browser window. A successful private-window attempt usually indicates stale browser state rather than an identity-provider outage.

## SAML validation

Verify that the assertion consumer service URL and entity ID exactly match the values shown in the administration portal. Confirm that the assertion is not expired and that both systems have accurate time. Clock drift greater than five minutes commonly produces a rejected assertion. Validate that the signing certificate is current and that the configured name identifier format matches the claim emitted by the identity provider.

Do not disable signature validation to work around a certificate problem. If a certificate expired, coordinate a planned certificate rotation and retain the previous certificate only for the documented overlap period.

## Escalation evidence

Escalate with the correlation ID, tenant ID, redacted assertion metadata, identity-provider logs, reproduction steps, and all configuration checks performed. Remove tokens, cookies, personal attributes, and certificate private material from attachments. Security Operations must be engaged immediately if logs show impossible travel, repeated MFA bypass attempts, or unauthorized changes to SSO configuration.
