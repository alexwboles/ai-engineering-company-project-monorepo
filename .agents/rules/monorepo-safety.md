# Rule: Monorepo Safety and Reuse

## Scope

Always active.

## Intent

Keep code consistent, avoid logic duplication, and preserve monorepo boundaries.

## Requirements

- Do not duplicate business logic already defined in apps/healthcore-backend.
- Import shared types from packages/shared where needed.
- New API/server endpoints must live under /services.
- UI applications under uis/ must remain isolated by purpose (public vs internal).
- If a change needs editing protected governance files, request explicit developer confirmation first.
