# AGENTS.md

## Required Startup Reads

At the start of every session, the agent must read these files in order:

1. memory-bank/projectbrief.md
2. memory-bank/techContext.md
3. memory-bank/progress.md
4. CONTEXT.md
5. CONTEXT_HEALTHCORE.md

## Mandatory Pre-Commit Workflow

Before every commit, the agent must complete these ordered steps:

1. Requirements check: map each request to concrete files and acceptance criteria.
2. Safety check: confirm protected paths are untouched unless explicit developer approval exists.
3. Verification check: run relevant lint/type/build commands for changed scopes and review errors.
4. Delivery check: summarize changes, call out risks/gaps, and confirm env/secrets policy compliance.

## Protected Paths (Require Explicit Developer Confirmation)

The agent must not modify these paths without explicit developer confirmation in the active conversation:

- packages/shared/index.ts
- CONTEXT.md
- CONTEXT_HEALTHCORE.md
- memory-bank/*
- AGENTS.md
- .agents/rules/*
- .agents/skills/*
- .github/*

## Development Conventions

- Prefer importing existing business logic instead of copying it.
- Place API code under /services.
- Keep .env.local untracked and maintain .env.example with required variables.
