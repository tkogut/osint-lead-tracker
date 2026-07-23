# PLAN-034: Update & Bump AGENTS-OS Core to v6.0 Swarm Edition

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Update `agents-os-core` repository (`/home/admin_tk/projects/agents-os-core`) and bump system version from `v5.0` to **`v6.0 Swarm Edition`**.
Incorporate the latest AGENTS-OS v6.1 Triad Governance (Mandatory dual handshakes Builder + Auditor, Coordinator source code prohibition, physical `smart_commit.sh` gate).

---

## 🏗️ Implementation Details

### 1. Governance & Template Updates (`/home/admin_tk/projects/agents-os-core`)
- Copy latest `GOVERNANCE.md` (v6.0/v6.1 with dual handshake enforcer) to `vault/.agents/rules/GOVERNANCE.md`.
- Copy updated `smart_commit.sh` (with mandatory `--require-roles builder,auditor`) to `vault/.agents/skills/git-pushing/scripts/smart_commit.sh`.

### 2. Version Bump (`v5.0` -> `v6.0`)
- Update `INSTALL.sh`: Update banner, version strings, and template path (`v6.0-swarm`).
- Update `os-init` & `os-add-skill`.
- Update `global_skills/swarm-bootstrapper/scripts/bootstrap.py`.
- Update `README.md`, `CHANGELOG.md`, `vault/.agents/specs/AGENTS-OS.md`.

### 3. Installation & Git Push
- Run `bash INSTALL.sh` to deploy `v6.0-swarm` template to `~/.antigravity/templates/v6.0-swarm`.
- Commit and push changes to `https://github.com/tkogut/agents-os-core` (branch `master`).

---

## 🛠️ Roles
- **Coordinator**: Plan creation, execution, git commit & push in `agents-os-core`.
