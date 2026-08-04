# HealthCore RFP Approval Workflow

Part 3 keeps the Part 1 ticket ID and Part 2 department drafts while adding a
durable, human-controlled completion stage.

- `start_approval_run` creates a namespaced thread (`rfp:{ticket_id}:approval:{run}`), checkpoints the full branch state in SQLite, and calls `interrupt` for each department.
- `resume` validates `approve`, `reject`, or `request_changes` and resumes only the selected department. Rejection and requested changes route that branch back through the existing Part 2 generator/evaluator loop, bounded by three revision attempts.
- `arbitrate_disagreements` is an explicit node. HealthCore's Revenue Cycle and Billing team owns commercial figures; Compliance and Data Governance owns patient-data controls. Conflicts are recorded and resolved by those rules rather than by agent voting.
- `ultimate_document_synthesizer` runs once, only after every required department is approved, and writes a Markdown artifact linked from the ticket.
- Every node writes an agent, input, output, and UTC timestamp to `rfp_approval_trace` in the same SQLite checkpoint database. `RFP_APPROVAL_CHECKPOINT_DB` can point to a durable Postgres-backed volume or a local SQLite path in development.

The backoffice uses the authenticated approval endpoints under
`/rfp/tickets/{ticket_id}/approvals`. The final proposal is available through
`/rfp/tickets/{ticket_id}/final-document` after the ticket reaches `done`.
