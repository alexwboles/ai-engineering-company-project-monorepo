# Technical Context

## Stack

- Monorepo with TypeScript-first modules.
- Next.js + React + TypeScript for UI applications under uis/.
- Shared domain types under packages/shared.
- Business logic utilities under apps/healthcore-backend/src/utils.

## Architectural Decisions

- Keep business logic in original module location and import it where needed.
- Maintain separate UI apps for public and internal use cases:
  - uis/website (public)
  - uis/backoffice (internal)
- Store persistent agent guidance in repository files:
  - memory-bank/*
  - AGENTS.md
  - .agents/rules/*
  - .agents/skills/*

## Constraints

- Avoid duplicating business logic code across apps.
- Keep .env.local out of git; document required variables in .env.example.
- Any API code must be placed under /services.
- Agent edits must follow explicit pre-commit workflow.
