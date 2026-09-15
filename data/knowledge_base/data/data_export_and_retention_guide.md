---
title: Customer Data Export and Retention Guide
document_id: DATA-GDE-118
department: Data Governance
product: Enterprise Platform
audience: Customer Support
version: 1.9
last_reviewed: 2026-06-19
tags: export, retention, deletion, privacy, compliance
---
# Customer Data Export and Retention Guide

Organization administrators can request a standard export from the administration portal. Exports may include account configuration, ticket records, audit events, and user-generated knowledge content, depending on enabled products and administrator permissions.

## Export troubleshooting

An export enters queued, processing, completed, or failed status. Large exports can remain processing for several hours. Confirm the export job ID, creation time, requesting administrator, selected data scope, and current status. Do not ask the customer to send the downloaded archive because it may contain confidential or regulated data.

Completed download links expire after seventy-two hours. If a link expires, an authorized administrator must create a new export. Support cannot extend or reactivate an expired link. If a job fails twice, escalate with the job ID and tenant ID; Engineering can inspect server-side diagnostics without receiving the archive.

## Retention and deletion

Default retention depends on the customer's contract and configured policy. Never state a universal retention period without checking the tenant policy. Legal holds override routine deletion schedules, and Support must not remove or alter a hold. Requests involving statutory deletion rights must be routed to the Privacy Operations queue for identity and authority verification.

Deletion is asynchronous and may pass through a recoverable state before permanent removal. Backups age out according to the controlled backup-retention schedule and are not selectively edited. Support should communicate the approved completion window from the privacy case rather than estimate a date.

Escalate suspected unauthorized exports, download-link exposure, or unexpected access to Security Operations immediately. Include the export job ID, actor, timestamp, and audit event IDs, but do not copy exported customer data into the incident record.
