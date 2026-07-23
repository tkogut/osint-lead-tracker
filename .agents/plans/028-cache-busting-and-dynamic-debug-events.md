# PLAN-028: Cache-Busting JS/CSS & Dynamic Debug Event Delegation

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Fix browser JS caching and tab click binding so that `app.js` is never served stale from browser cache, and `res.debug_info` reliably updates `#sandbox-debug-content`.

---

## 🏗️ Implementation Details
1. **Cache-Busting Query Strings (`src/static/index.html`)**:
   - Update `<script src="/static/app.js?v=1.7.6">` and `<link rel="stylesheet" href="/static/styles.css?v=1.7.6">`.
2. **Event Delegation (`src/static/app.js`)**:
   - Change `.debug-tab-btn` click listeners from one-time `querySelectorAll` to document-level event delegation (`document.addEventListener("click", ...)`).
3. **Automated Bumper (`scripts/bump_patch_version.py`)**:
   - Update regex replacements to automatically bump `app.js?v=...` and `styles.css?v=...` in `index.html` on every patch version bump.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, script integration, handshake validation, smart commit.
- **Builder (Subagent)**: Implement cache-busting and event delegation, update `bump_patch_version.py`, verify syntax, and generate builder handshake.
