# PLAN-026: Automatic Patch Version Bumping in Framework & smart_commit.sh

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Automate patch version incrementing (`1.7.x` -> `1.7.x+1`) on every commit via `smart_commit.sh` so that every deployment/rebuild updates the top-left UI badge (`OSINT v1.7.x`) and `/health` API endpoint. Major/minor bumps (`1.8`, `1.9`...) will remain manual upon explicit user request.

---

## 🏗️ Implementation Details
1. Create `scripts/bump_patch_version.py`:
   - Reads current version from `src/main.py` (e.g. `1.7.2`).
   - Increments patch number (`1.7.2` -> `1.7.3`).
   - Updates version strings in `src/main.py`, `src/static/index.html`, `README.md`.
   - Appends entry in `CHANGELOG.md` for current date.
2. Update `.agents/skills/git-pushing/scripts/smart_commit.sh`:
   - Integrates `python3 scripts/bump_patch_version.py` before `git add .`.
3. Bump current version to `1.7.3` immediately for Plan 025/026 changes.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, script integration in `smart_commit.sh`, handshake verification, git push.
- **Builder (Subagent)**: Implement `scripts/bump_patch_version.py`, update initial version files to `1.7.3`, verify syntax & generate handshake.
