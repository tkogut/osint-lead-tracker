# Execution Plan — deploy-to-vps skill (workspace deploy convention)

**Slug:** `deploy-to-vps-skill`
**Branch:** `feat/deploy-to-vps-skill`
**Date:** 2026-10-07
**Engine:** om-auto-create-pr (plain)

## Goal

Turn the one-off "automatic VPS deploy" workflow (PR #1) into a reusable workspace
convention so every project can adopt it consistently, and make the existing
`om-setup-agent-pipeline` propose it — without editing the upstream `om-*` skill.

## Scope

- New portable skill `.agents/skills/deploy-to-vps/` containing:
  - `SKILL.md` — the convention, secret/variable reference, canonical (corrected)
    setup commands, distribution guidance and guardrails;
  - `assets/deploy.yml` — parameterised template of the workflow from PR #1;
  - `scripts/setup-deploy-secrets.sh` — interactive, non-destructive helper for
    `ssh-keygen` → `ssh-copy-id` → verify → `gh secret set VPS_SSH_KEY` (+ optional
    `VPS_SSH_PASSPHRASE`) → repo variables.
- Repo-local override `.ai/skills/om-setup-agent-pipeline/SKILL.md` adding a
  "propose deploy.yml" step via the supported per-skill override mechanism.
- Pointer in `.agents/skills/vps-ops/SKILL.md` and a decision entry in
  `.agents/MEMORY.md`.

## Non-goals

- No changes to the app, Dockerfile or `docker-compose.yml`.
- No secrets or SSH keys are created by this PR (the script is the user's tool).
- Distribution into `agents-os-core` (the canonical AGENTS-OS source is not present
  in this environment); the skill documents the copy step instead.

## Key decisions

- **Separate skill, not an edit to `om-setup-agent-pipeline`.** The upstream skill
  is installed from `open-mercato/skills` and overwritten on upgrade; workspace
  specifics (fixed host, owner, SSH flow) must not live there. The official
  repo-local override hooks the behaviour in safely.
- **Not stored only in `MEMORY.md`.** Memory is per-project and union-merged; a new
  project would not inherit it. The skill is the carrier, memory only points to it.
- **Corrected the secret-setup commands** so the key filename is identical across
  `ssh-keygen` / `ssh-copy-id` / `gh secret set` (the common failure).

## Implementation Plan

### Phase 1: Portable skill

- [x] 1.1 Author `.agents/skills/deploy-to-vps/SKILL.md`
- [x] 1.2 Add `assets/deploy.yml` (parameterised template, validated)
- [x] 1.3 Add `scripts/setup-deploy-secrets.sh` (interactive, safe)

### Phase 2: Hook and pointers

- [x] 2.1 Repo-local override `.ai/skills/om-setup-agent-pipeline/SKILL.md`
- [x] 2.2 Pointer in `vps-ops/SKILL.md` + decision entry in `.agents/MEMORY.md`
- [x] 2.3 Run the configured validation gate

## Risks

- **Adoption drift.** `vps-ops/SKILL.md` already differs across projects; the new
  skill must be copied to the canonical AGENTS-OS source to avoid divergence.
  Documented in the skill's Distribution section.
- **Scope creep of the setup hook.** The override is advisory and never creates
  secrets autonomously; the script confirms each mutation.

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

**PR:** #2

### Phase 1: Portable skill

- [x] 1.1 Author `.agents/skills/deploy-to-vps/SKILL.md` — d780583
- [x] 1.2 Add `assets/deploy.yml` (parameterised template, validated) — d780583
- [x] 1.3 Add `scripts/setup-deploy-secrets.sh` (interactive, safe) — d780583

### Phase 2: Hook and pointers

- [x] 2.1 Repo-local override `.ai/skills/om-setup-agent-pipeline/SKILL.md` — d780583
- [x] 2.2 Pointer in `vps-ops/SKILL.md` + decision entry in `.agents/MEMORY.md` — d780583
- [x] 2.3 Run the configured validation gate — 36 passed
- [x] Post-merge fix (from main `3b1af37`): bind-mounted `data/` ownership for the container's non-root user — `chown`/`chmod` in the template + `__DATA_UID__` placeholder documented
