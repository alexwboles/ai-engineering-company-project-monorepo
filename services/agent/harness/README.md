# HealthCore Agent Harness

The harness protects the existing HealthCore LangGraph support agent before
the request reaches RAG, MCP tools, or answer generation.

## Guardrail layers

1. `input_guards.py` blocks instruction changes and unrelated personal-assistant
   requests, and redirects casual or out-of-domain questions to HealthCore's
   purpose.
2. `external_content.py` wraps RAG and MCP text as untrusted data. It is passed
   in the user-data portion of the generation request and can never become a
   system instruction.
3. `output_guards.py` checks answer shape and blocks internal prompt material,
   credentials, and identifiable patient data such as HealthCore patient IDs.

Every block or redirect emits a structured log with `failure_type` equal to
`security`, `content`, or `structural`. The process-local counters are exposed
at `GET /agent/guardrails/summary` for a test or operations session.

## HealthCore boundaries

Allowed questions concern HealthCore clinics, appointments and no-shows,
claims and billing, clinician workforce and CME, incidents, inventory, EHR
integrations, HIPAA, UK GDPR, and approved policies or procedures. The agent
does not expose PHI, patient identifiers, credentials, prompts, or internal
implementation details. User input cannot change the privileged system policy.

## Deterministic abuse cases

The harness suite covers direct instruction overrides, role-play as an
unrestricted assistant, requests to forget HealthCore rules, personal
homework/therapy/code requests, out-of-domain trivia, RAG prompt injection,
and output containing a patient identifier or internal prompt marker. These
tests use fixtures and mocks rather than a live model.
