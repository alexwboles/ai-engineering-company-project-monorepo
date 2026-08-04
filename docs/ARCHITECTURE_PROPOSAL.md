# Architecture Proposal

## 1. Context and Goal

HealthCore now has a public web presence, internal backoffice workflows, and business logic modules in a monorepo. The next backend should support multi-domain operations (candidate pipeline, billing metrics, no-show analytics, and clinician compliance) with clear ownership and low coordination overhead for a small engineering team.

This document defines a backend architecture proposal before coding begins, including pattern choice, module boundaries, router organization, and operational risks.

## 2. Proposed Architectural Pattern

### 2.1 Pattern

Domain-oriented modular monolith with layered responsibilities inside each domain.

### 2.2 Why This Fits HealthCore (Business-Tied Justification)

- HealthCore is operationally complex but team-constrained: one deployable backend keeps complexity manageable while still allowing domain separation for People and Workforce, Revenue Cycle, Patient Access, and Compliance workflows.
- The company operates in US and UK contexts with policy-sensitive data handling. A modular monolith allows consistent cross-cutting controls (logging, auth policy, validation, audit metadata) in one runtime.
- Current milestone cadence needs fast iteration and predictable handoffs. A single service with strict domain boundaries avoids premature distributed-system cost while preserving a migration path if one domain later needs independent scaling.
- Existing monorepo assets already separate concerns by business logic and UI surfaces. The backend should mirror that by using domain modules instead of controller-centric sprawl.

### 2.3 Why Not Start with Microservices

- The current stage does not justify independent deployment pipelines, service contracts, inter-service observability, and failure handling overhead.
- For HealthCore right now, speed of change and consistency of governance are higher-value than independent horizontal scaling.

## 3. Proposed Backend Folder and Module Structure

The backend should live as a dedicated project in the monorepo, for example under `services/healthcore-api/`.

```text
services/
  healthcore-api/
    app/
      main.py
      core/
        config.py
        security.py
        logging.py
        exceptions.py
      dependencies/
        auth.py
        pagination.py
      routers/
        people_workforce.py
        candidate_pipeline.py
        billing.py
        appointments.py
        clinicians.py
        compliance.py
        health.py
      schemas/
        people_workforce.py
        candidate_pipeline.py
        billing.py
        appointments.py
        clinicians.py
        compliance.py
      services/
        people_workforce_service.py
        candidate_pipeline_service.py
        billing_service.py
        appointments_service.py
        clinicians_service.py
        compliance_service.py
      repositories/
        people_workforce_repository.py
        candidate_pipeline_repository.py
        billing_repository.py
        appointments_repository.py
        clinicians_repository.py
      models/
        people_workforce.py
        candidate_pipeline.py
        billing.py
        appointments.py
        clinicians.py
      integration/
        milestone2_adapter.py
        website_adapter.py
        backoffice_adapter.py
      tests/
        test_people_workforce.py
        test_billing.py
```

### 3.1 Separation Criteria

- Routers: HTTP interface grouped by business domain.
- Schemas: request and response contracts per domain.
- Services: domain use-cases and orchestration rules.
- Repositories: persistence and query abstraction.
- Core and dependencies: shared technical concerns only.
- Integration: adapters for existing monorepo modules and future external systems.

This keeps technical layering clear without losing business-domain clarity.

## 4. FastAPI Endpoint and Router Organization

### 4.1 Router Grouping Principle

Group routes by business domain, not by HTTP verb or by UI page.

### 4.2 Initial Domain Route Map (No Code, Structure Only)

- `people_workforce`
  - `/people-workforce/roles`
  - `/people-workforce/teams`
  - `/people-workforce/capacity`
- `candidate_pipeline`
  - `/candidate-pipeline/candidates`
  - `/candidate-pipeline/candidates/{candidate_id}`
  - `/candidate-pipeline/candidates/{candidate_id}/notes`
- `billing`
  - `/billing/claims`
  - `/billing/denial-rates`
  - `/billing/denial-rates/by-payer`
- `appointments`
  - `/appointments`
  - `/appointments/no-show-impact`
  - `/appointments/no-show-rates/by-location`
- `clinicians`
  - `/clinicians`
  - `/clinicians/cme-report`
  - `/clinicians/expiring-licenses`
- `compliance`
  - `/compliance/policies`
  - `/compliance/audit-events`
  - `/compliance/access-reviews`
- `health`
  - `/health/live`
  - `/health/ready`

### 4.3 API Versioning Strategy

- Prefix domain routers under `/api/v1` from day one to avoid breaking clients when adding `/api/v2` later.
- Keep versioning at router inclusion level rather than hardcoding versions into every handler path.

## 5. FastAPI Standards Research and Influence on Design

The structure above is directly influenced by FastAPI guidance for larger applications.

### 5.1 Standards Identified

- Use multiple files and packages instead of a single monolithic module.
- Use `APIRouter` instances per functional area and include them in `main`.
- Keep reusable dependencies in dedicated modules.
- Keep settings/config in dedicated modules and load environment-driven config centrally.

### 5.2 How This Changes Decisions Here

- Domain routers are explicit and separate because FastAPI supports composition through `include_router`.
- Shared dependency logic is centralized under `dependencies/` rather than duplicated in handlers.
- Runtime configuration is centralized in `core/config.py` to keep environment management consistent across deploys.

## 6. Frontend and Backend as Separate Systems

HealthCore should treat frontend and backend as separate systems that coexist in one monorepo.

### 6.1 Communication Contract

- Frontends in `uis/` consume backend endpoints over HTTP using explicit DTO schemas.
- Backend should publish stable endpoint contracts per domain and version (`/api/v1/...`).

### 6.2 CORS and Origin Policy

- Allow explicit frontend origins only.
- Avoid wildcard origins for credentialed requests.
- Distinguish local development origins and production origins via environment variables.

### 6.3 Environment Variable Management

- Keep environment-specific values out of code and out of committed secrets.
- Keep `.env.example` as contract documentation and use real secret values outside version control.
- Use granular variables per deploy stage instead of broad grouped environment assumptions.

### 6.4 Monorepo Boundary Rules

- Backend project lives under `services/`.
- UI projects under `uis/` must not import backend internals directly.
- Shared contracts should be defined in common package modules when needed.

## 7. Risks and Points of Attention

### 7.1 Risk 1: Domain Leakage Across Modules

If teams bypass domain boundaries (for example, billing logic inside candidate modules), velocity will drop due to hidden coupling and difficult testing.

Mitigation:

- Enforce router and service ownership by domain.
- Require review checks for cross-domain imports.

### 7.2 Risk 2: Inconsistent API Contracts Between Frontend and Backend

If schema changes are introduced informally, frontends can break silently and operational dashboards will become unreliable.

Mitigation:

- Version endpoint groups.
- Keep request and response schemas in explicit domain files.
- Include contract checks in CI before merges.

### 7.3 Risk 3: Misconfigured CORS and Environment Variables

Incorrect origin settings can block frontends in production or accidentally overexpose endpoints. Mismanaged environment variables can leak credentials.

Mitigation:

- Use explicit origin allowlists by deploy stage.
- Keep secrets out of repo and document required variables in `.env.example`.

### 7.4 Risk 4: Premature Service Fragmentation

Splitting domains into microservices too early can increase latency, operational burden, and ownership confusion.

Mitigation:

- Start as modular monolith.
- Define objective split triggers (team size, independent scaling need, release bottlenecks).

## 8. Initial Technical Decisions to Lock Before Sprint Start

- Pattern: domain-oriented modular monolith.
- Backend location: `services/healthcore-api/`.
- Router grouping: by business domain under `/api/v1`.
- Cross-cutting module locations: `core/`, `dependencies/`.
- Frontend-backend interaction model: HTTP contract with explicit CORS and environment configuration.

## 9. Sources and Research Basis

- [FastAPI, Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI, CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [FastAPI, Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)
- [The Twelve-Factor App, Config](https://12factor.net/config)
- [MDN CORS reference (as cited by FastAPI CORS page)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
