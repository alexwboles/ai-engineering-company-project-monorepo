# Project Brief

## Business Description

HealthCore is a two-country outpatient healthcare network (US and UK) with operational pain points in recruiting, claims denial tracking, no-show losses, and clinician CME compliance.

## Project Objectives

- Build and maintain a unified monorepo foundation for public and internal products.
- Keep business context and technical context persistent for coding agents.
- Deliver a reusable UI platform for customer-facing and internal workflows.
- Reuse existing business logic modules instead of duplicating logic.

## Problem This Solves

Without persistent context and guardrails, agent output becomes inconsistent and risky. Without a coherent monorepo structure, features are delivered in isolation and become hard to scale.

## Current Scope

- Public website in uis/website.
- Internal operational app in uis/backoffice.
- Agent infrastructure via memory-bank, AGENTS.md, .agents/rules, and .agents/skills.
- Business logic imported from apps/healthcore-backend.
