# Telemetry Plan

## Scope

This plan is written against the current HealthCore monorepo context in this repository. The mandatory baseline comes from the project context files and covers billing, appointments, clinician compliance, and data-quality validation. Around that floor, the catalogue expands into auth, navigation, performance, supplier management, and incident workflow telemetry so the team can answer both today's operational questions and tomorrow's unknowns.

## Event Envelope

Every event must use the same envelope before it reaches storage or a stream processor:

- `eventId`: UUID v4 generated at emit time.
- `timestamp`: ISO 8601 UTC timestamp.
- `sessionId`: opaque session identifier for the active browser or API session.
- `userId`: opaque internal user identifier, or `null` when the actor is anonymous.
- `event_type`: `entity_action` naming convention, lower snake case.
- `schemaVersion`: semantic version for the event payload schema.
- `requestId`: request correlation ID shared across frontend, backend, and logs.
- `properties`: event-specific payload that must obey the allowlist for that event.

Envelope rules:

- Reject any event that contains keys outside the documented allowlist for that event.
- Keep `userId` and `sessionId` opaque; never use email, name, or other direct identifiers.
- Propagate `requestId` from frontend to backend so telemetry can be joined to traces and logs.
- Increment `schemaVersion` only when a breaking payload change is introduced.

## Delivery Rules

- Use `stream` when the event changes an operational decision quickly, such as a denial, a failed login, or a validation error.
- Use `batch` when the event is a roll-up metric or a periodic health snapshot, such as denial rate or no-show impact.
- High-frequency events must be throttled or deduplicated:
  - `navigation_section_opened`: emit once per route change and suppress repeat opens for 30 seconds per session and section.
  - `api_latency_recorded`: aggregate by route, method, and status code in 60-second windows.
  - `frontend_error_occurred` and `backend_unhandled_exception`: deduplicate by error fingerprint for 5 minutes.
  - `workflow_abandoned`: emit once after 15 to 30 seconds of inactivity or on route exit, whichever comes first.

## Mandatory Baseline

These are the required signals from the repository context. They are the floor, not the ceiling.

| Event type | Why we capture it | Delivery | Property allowlist | PII / sensitive handling |
| --- | --- | --- | --- | --- |
| `claim_submitted` | We capture `claim_submitted` because we need to know whether claims are entering the system with the right payer, location, and service mix, which allows us to tune pre-submission validation and coding review. | Stream | `claimId`, `locationId`, `payerId`, `payerName`, `serviceType`, `claimAmount`, `resubmitted`, `submissionChannel` | No direct PII; use opaque IDs only. |
| `claim_denied` | We capture `claim_denied` because we need to know which payer/location combinations and denial reasons are creating the most rework, which allows us to prioritize appeals and staff coding follow-up. | Stream | `claimId`, `locationId`, `payerId`, `denialReason`, `resubmitted`, `claimAmount`, `daysSinceSubmission`, `appealEligible` | No direct PII; never emit member names or notes. |
| `claim_validation_failed` | We capture `claim_validation_failed` because we need to know which fields and sources are failing validation, which allows us to fix rules before bad claims reach downstream processing. | Stream | `claimId`, `locationId`, `validationErrors`, `invalidFields`, `source`, `severity` | No PII; include only field names and error codes, not raw payloads. |
| `appointment_scheduled` | We capture `appointment_scheduled` because we need to know where and how visits are booked, which allows us to adjust access, reminders, and staffing assumptions. | Stream | `appointmentId`, `locationId`, `serviceType`, `scheduledDate`, `scheduledTime`, `channel`, `leadTimeHours` | No direct PII; do not include patient name or contact details. |
| `appointment_no_show_marked` | We capture `appointment_no_show_marked` because we need to know which services, locations, and reminder patterns correlate with no-shows, which allows us to target outreach and schedule design. | Stream | `appointmentId`, `locationId`, `serviceType`, `noShowReasonCode`, `reminderCount`, `rescheduled` | No direct PII; use coded reasons only. |
| `appointment_completed` | We capture `appointment_completed` because we need to know which visits actually close the loop, which allows us to measure throughput and compare completion versus cancellation or no-show. | Stream | `appointmentId`, `locationId`, `serviceType`, `visitDurationMinutes`, `confirmedAtDeltaMinutes`, `staffedByRole` | No direct PII; keep the payload to operational fields only. |
| `clinician_cme_logged` | We capture `clinician_cme_logged` because we need to know how quickly clinicians accumulate hours and from which source, which allows us to intervene before compliance risk grows. | Stream | `clinicianId`, `role`, `cmeHoursLogged`, `cmeHoursRequired`, `source`, `cycleYear` | No direct PII; clinician IDs stay internal and opaque. |
| `clinician_compliance_calculated` | We capture `clinician_compliance_calculated` because we need to know who is on track, at risk, or overdue, which allows us to focus compliance follow-up on the right people first. | Batch | `clinicianId`, `role`, `cmeHoursLogged`, `cmeHoursRequired`, `complianceStatus`, `hoursRemaining`, `daysUntilLicenceExpiry` | No direct PII; this is aggregate compliance status only. |
| `billing_denial_rate_calculated` | We capture `billing_denial_rate_calculated` because we need to know denial rates by payer and location, which allows us to reallocate denial-management effort and spot contract issues early. | Batch | `payerId`, `payerName`, `locationId`, `periodStart`, `periodEnd`, `totalClaims`, `deniedClaims`, `denialRate` | No direct PII; report aggregates only. |
| `no_show_impact_calculated` | We capture `no_show_impact_calculated` because we need to know where missed visits are costing the business the most, which allows us to focus reminder and access improvements on the highest-impact locations. | Batch | `locationId`, `periodStart`, `periodEnd`, `scheduledAppointments`, `noShowCount`, `noShowRate`, `estimatedLostRevenue` | No direct PII; report location-level aggregates only. |

## Additional Opportunities

These events are not the minimum required baseline, but they are high-value opportunities that expand observability across the monorepo.

| Event type | Why we capture it | Delivery | Property allowlist | PII / sensitive handling |
| --- | --- | --- | --- | --- |
| `auth_login_attempted` | We capture `auth_login_attempted` because we need to know how often users try to authenticate and from which client surfaces, which allows us to detect friction before it becomes support load. | Stream | `authMethod`, `clientApp`, `userRole`, `authProvider`, `mfaUsed` | No direct PII; never emit raw email or password. |
| `auth_login_failed` | We capture `auth_login_failed` because we need to know whether failures are caused by bad credentials, lockouts, or system errors, which allows us to tune lockout rules and login UX. | Stream | `authMethod`, `clientApp`, `userRole`, `failureReason`, `lockoutTriggered`, `attemptCount` | No direct PII; use failure codes only. |
| `auth_session_expired` | We capture `auth_session_expired` because we need to know when and why sessions lapse, which allows us to balance security timeouts against operator inconvenience. | Stream | `sessionAgeMinutes`, `authMethod`, `clientApp`, `expiryReason` | No direct PII; session IDs remain opaque. |
| `navigation_section_opened` | We capture `navigation_section_opened` because we need to know which sections operators visit most, which allows us to improve layout, prioritization, and training. | Stream | `sectionName`, `route`, `previousRoute`, `userRole`, `entryPoint` | No direct PII; section and route names only. |
| `workflow_abandoned` | We capture `workflow_abandoned` because we need to know where users drop out mid-flow, which allows us to shorten forms, clarify validation, and remove dead ends. | Stream | `flowName`, `stepName`, `lastCompletedStep`, `timeSinceStartSeconds`, `exitRoute`, `userRole` | No direct PII; no form contents or free-text notes. |
| `api_latency_recorded` | We capture `api_latency_recorded` because we need to know which endpoints are slowing operators down, which allows us to prioritize backend tuning and caching work. | Batch | `route`, `method`, `statusCode`, `durationMs`, `domain`, `requestSizeBytes`, `responseSizeBytes` | No direct PII; transport metrics only. |
| `frontend_error_occurred` | We capture `frontend_error_occurred` because we need to know which pages and components are breaking in the browser, which allows us to fix usability issues before they become support incidents. | Stream | `pageRoute`, `componentName`, `errorClass`, `errorFingerprint`, `recoverable`, `actionTaken` | No raw stack traces or payloads; fingerprint only. |
| `backend_unhandled_exception` | We capture `backend_unhandled_exception` because we need to know which code paths are failing server-side, which allows us to fix defects and protect user flows before they spread. | Stream | `route`, `exceptionClass`, `errorFingerprint`, `requestMethod`, `statusCode`, `workerId` | No stack traces in telemetry; send fingerprints and sanitized metadata only. |
| `supplier_rate_updated` | We capture `supplier_rate_updated` because we need to know when procurement prices move, which allows us to detect margin pressure and renegotiate with the right suppliers. | Stream | `supplierId`, `previousRate`, `newRate`, `country`, `category`, `updatedByRole` | No direct PII; supplier IDs are internal only. |
| `incident_status_changed` | We capture `incident_status_changed` because we need to know how incidents move through the workflow, which allows us to identify bottlenecks and stuck cases quickly. | Stream | `incidentId`, `previousStatus`, `nextStatus`, `origin`, `category`, `actorRole`, `timeInPreviousStatusHours` | No direct PII; incident identifiers only. |

## What Not To Capture

- Do not capture passwords, reset tokens, session secrets, or API keys.
- Do not capture raw request bodies, CSV contents, free-text notes, or stack traces.
- Do not emit email addresses, patient names, phone numbers, or any other direct identifiers when an opaque ID will do.
- Do not allow unknown keys in `properties`; the collector should reject or drop them before storage.
- Do not use telemetry as a replacement for audit logging. Keep security/audit events separate if they need stricter retention or access rules.

## Why This Plan Is Implementable Tomorrow

- The mandatory baseline is tied to the repository's existing business entities and workflows, so the first instrumentation pass can be mapped directly onto current claims, appointments, and clinician code paths.
- The extra catalogue covers the rest of the app surfaces already present in the monorepo, including authentication, navigation, supplier management, incident handling, and reliability signals.
- The envelope is stable and reusable, so any future event can be added without changing the ingestion contract.
- The allowlists are strict enough to prevent accidental leakage and simple enough for another developer to implement without ambiguity.
