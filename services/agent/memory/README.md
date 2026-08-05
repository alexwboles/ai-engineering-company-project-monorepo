# HealthCore Agent Memory

## Architecture decision

The support agent uses a SQLite key-value store through `MemoryStore`. HealthCore
needs durable, exact recall for short de-identified operational corrections and
reusable incident-resolution patterns, not a second copy of the policy corpus.
RAG remains the semantic store for approved HealthCore documents; a knowledge
graph is unnecessary because these memories do not represent entity
relationships; fine-tuning would make selective correction and deletion harder.
SQLite is persistent across API/worker restarts, works without another service,
and gives the proposal/audit flow transactional storage. `HEALTHCORE_MEMORY_DB`
configures its path.

## What may be remembered

- De-identified corrections to HealthCore operational policies or procedures.
- Reusable patterns for resolving HealthCore support incidents.
- Stable workflow clarifications for appointments/no-shows, claims/billing,
  compliance, CME/workforce, inventory, and EHR operations.

## What must never be remembered

The policy rejects patient identifiers (`HC-XXXXXX`), email addresses, phone
numbers, SSNs, diagnoses, patient records, employee salaries, credentials,
passwords, API keys, tokens, secrets, and internal prompts. An explicit user
approval cannot override this policy. HealthCore HIPAA and UK GDPR obligations
make this a hard boundary, not a best-effort filter.

## Proposal and confirmation lifecycle

1. The same agent turn applies an explicit self-evaluation criterion: a reusable
   HealthCore correction/update signal, a HealthCore topic, a safe answer, and
   no forbidden data. It returns a structured `memory_proposal` field and asks
   the user in the same response. It does not write yet.
2. One `pending_proposals` row is allowed per `session_id`. The next message is
   classified as `approve`, `edit`, `reject`, or `unclear` by the confirmation
   classifier. A bare topic change or ambiguous response becomes rejection by
   default; silence never approves.
3. Only `approve` or a safe `edit` calls `MemoryStore.write`. Every proposal and
   outcome is recorded in `memory_audit` with the originating message, user
   decision, timestamp, reason, and `written` flag.
4. Approved entries are read on later turns and wrapped as untrusted data before
   they reach the generation step. They cannot become system instructions.

## Consolidation and cleanup

Entries upsert by a deterministic topic key, so a corrected policy replaces the
older fact instead of duplicating it. Entries expire after 90 days by default,
and consolidation evicts the oldest records above the 100-entry cap. This keeps
short-lived operational guidance useful without allowing unlimited accumulation.
`MemoryStore.consolidate()` is callable by a scheduled cleanup job or an admin
maintenance command.

## Non-memorable examples

The agent dismisses a one-off question such as “What is the HealthCore denial
rate?”, a thank-you/closing such as “Thanks for your help,” and any patient-
specific correction containing an identifier. The first two have no explicit
reusable correction signal; the last violates the PHI policy.

## Evidence cycles

- **Approved:** a user corrects the no-show reminder workflow, the response asks
  for approval, no row exists before approval, `approve` writes and audits it,
  and a later no-show question receives the stored correction.
- **Rejected:** a user proposes a billing workflow correction, replies `no`, the
  audit records rejection while the memory table remains empty, and a later
  billing question does not receive the rejected fact.

This is one agent with one additional structured memory field and explicit
store boundaries; a second agent would add no value to proposal classification.
