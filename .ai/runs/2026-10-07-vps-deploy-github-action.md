# Execution Plan — GitHub Actions auto-deploy to VPS

**Slug:** `vps-deploy-github-action`
**Branch:** `feat/vps-deploy-github-action`
**Date:** 2026-10-07
**Engine:** om-auto-create-pr (plain)

## Goal

Add a GitHub Actions workflow to `osint-lead-tracker` that automatically deploys the
application to the Hostinger VPS (`srv1490214.hstgr.cloud`) on every push to `main`,
mirroring the existing `tkogut/linkedin-tracker` `.github/workflows/deploy.yml`
(checkout → copy the repository to the VPS → rebuild and restart the Docker Compose
stack). The workflow must be safe to run repeatedly, must not clobber the server's
`.env`, and must verify the container becomes healthy after the rebuild.

## Scope

- New workflow file `.github/workflows/deploy.yml` (triggers on `push` to `main` plus
  a manual `workflow_dispatch`).
- Reuse the reference action shape: `appleboy/scp-action` to ship the checkout to the
  VPS, then `appleboy/ssh-action` to run `docker compose up -d --build` and do a
  post-deploy health check.
- Document the required secret (`VPS_SSH_KEY`) and the optional repository variables
  in `README.md`.
- Non-secret defaults live in the workflow, matching the reference and the values
  already public in `docker-compose.yml`: host `srv1490214.hstgr.cloud`, user `root`,
  port `22`, target `/opt/osint-lead-tracker`.

## Non-goals

- No CI test workflow (this repository currently has none; out of scope).
- No changes to application code, `Dockerfile`, or `docker-compose.yml`.
- No automatic rollback / blue-green deploy — a single-container rebuild, as in the
  reference workflow.
- No Terraform/Ansible or VPS provisioning; the target directory and `.env` are
  expected to exist (or be recoverable) on the server.

## Key decisions

- **Deploy path default `/opt/osint-lead-tracker`.** The reference project deploys to
  `/opt/linkedin-tracker`; this mirrors that convention. It is overridable via the
  repository variable `DEPLOY_PATH` because the exact current path of the running
  stack on the VPS was not discoverable from the repo. Documented in README.
- **`.env` is never shipped.** `.env` is gitignored, so it is absent from the runner
  checkout and SCP leaves the server copy untouched. If it is missing, the remote
  script recovers values from the running container's environment (same technique as
  the reference), then falls back to `.env.example` with a loud warning.
- **`rm -rf .git` before SCP** so the checkout's git metadata is not tarred over the
  server directory (the reference's `source: "**"` otherwise includes `.git`).
- **Health verification after rebuild** (`curl /health` retry loop) instead of the
  reference's app-specific `run_scrape.py`, which does not exist in this project.
- **`concurrency` guard** so two pushes cannot run overlapping rebuilds on the host.
- **Configurable via `vars.*` with hard-coded fallbacks** — keeps the "just add one
  secret and it works" property of the reference while allowing overrides without
  editing the workflow.

## Implementation Plan

### Phase 1: Deploy workflow

- [ ] 1.1 Author `.github/workflows/deploy.yml` (triggers, concurrency, scp step, ssh rebuild + health check)
- [ ] 1.2 Validate the YAML parses and review trigger/secret wiring

### Phase 2: Documentation and validation

- [ ] 2.1 Document the deploy workflow, `VPS_SSH_KEY` secret and optional variables in `README.md`
- [ ] 2.2 Run the configured validation gate (`py_compile`, handshake validation, pytest)

## Risks

- **Existing stack path unknown.** If the running container was started from a
  different directory, the first run deploys to `/opt/osint-lead-tracker` and recreates
  the container (same `container_name`), potentially with an empty `./data` volume.
  Mitigation: path is overridable via `vars.DEPLOY_PATH`; README calls this out and the
  reviewer must confirm the server path before the first production run.
- **SSH key secret required.** Without `VPS_SSH_KEY` the workflow fails at the SCP step;
  documented.
- **`.env` recovery.** If neither a running container nor `.env` exists, the app starts
  with `.env.example` placeholders until the operator fills them in; the script logs a
  warning.

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

**PR:** #1

### Phase 1: Deploy workflow

- [x] 1.1 Author `.github/workflows/deploy.yml` (triggers, concurrency, scp step, ssh rebuild + health check) — c5c00df
- [x] 1.2 Validate the YAML parses and review trigger/secret wiring — c5c00df

### Phase 2: Documentation and validation

- [x] 2.1 Document the deploy workflow, `VPS_SSH_KEY` secret and optional variables in `README.md` — 243efb0
- [x] 2.2 Run the configured validation gate (`py_compile`, handshake validation, pytest) — 36 passed
- [x] Post-review fix (om-auto-review-pr): POSIX-safe `set -eu`, container HEALTHCHECK probe, job timeout, comment/README wording — 6d9461e
