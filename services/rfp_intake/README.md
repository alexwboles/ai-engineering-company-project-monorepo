# HealthCore RFP Intake

The intake pipeline is intentionally split into separate agent boundaries:

1. `convert.py` converts the uploaded PDF to Markdown before any agent reads it.
2. `metrics.py` stores issuer, deadline, HealthCore departments mentioned, page/word counts, and readability grades.
3. `agents/classifier.py` is a hard gate. It requires an RFP marker plus scope/requirements, deadline, and commercial signals. A rejected document is stored as `discarded` with a reason and never reaches orchestration.
4. `agents/orchestrator.py` assigns Markdown section slices to the HealthCore departments from `CONTEXT.md`.
5. `agents/workers/department_worker.py` receives only its assigned slice and produces department-specific aspects, questions, and contact roles.
6. `agents/synthesizer.py` creates the Sales-facing routing summary and the `proposal_generation_queue` handoff marker.

Unknown department mentions do not invalidate an otherwise valid RFP. They create a clarification workstream for Technology so James Osei's team can route the request safely. Workers do not receive the full PDF or full Markdown document. If workers disagree, both pieces of evidence remain in the synthesized department row so Sales can resolve the contradiction with that lead instead of losing it in a single overwritten answer.

The ticket is persisted in TinyDB and records every status transition. Upload starts at `analyzing`, successful classification enters `waiting_for_approval` while workstreams are prepared, and synthesis ends at `done`. A failed conversion or agent run is explicit `failed`; a classifier rejection is explicit `discarded`.
