# Skill: Milestone Checkpoint Audit

## Objective
Run a repeatable milestone readiness audit against explicit assignment requirements before delivery.

## Inputs
- A requirements list (bulleted or screenshot-transcribed).
- Target paths to verify (for example: uis/website, uis/backoffice, memory-bank, AGENTS.md, .agents).
- Validation commands to run (for example: npm run build, npm run lint).

## Output
- A checklist report with each requirement marked: PASS, PARTIAL, or FAIL.
- Evidence for each item: file paths and command outcomes.
- A minimal list of remediation actions for non-pass items.

## Acceptance Criteria (Verifiable)
- The report covers 100% of provided requirements.
- Every PASS item includes at least one concrete file reference.
- Every PARTIAL/FAIL item includes a specific fix action.
- The report includes command validation results for each executable app in scope.
