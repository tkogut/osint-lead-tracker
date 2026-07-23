# PLAN-033: Physical Enforcer of Auditor & Builder Handshake in Smart Commit

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Hardcode physical enforcement of BOTH `builder` AND `auditor` handshakes in `smart_commit.sh` and governance rules. Git commit/push will be physically blocked by shell execution unless both Builder AND Auditor subagents have completed their tasks and generated valid handshakes.

---

## 🏗️ Implementation Details

### 1. Hard Shell Enforcer (`.agents/skills/git-pushing/scripts/smart_commit.sh`)
- Change line 26 from:
  `python3 "$VALIDATE_SCRIPT" --require-roles builder`
  to:
  `python3 "$VALIDATE_SCRIPT" --require-roles builder,auditor`
- Update error messages to state: `❌ [Handshake Gate] BRAK lub NIEPOPRAWNY handshake od roli Builder lub Auditor!`.

### 2. System Rules (`.agents/rules/GOVERNANCE.md` & `GEMINI.md`)
- Update Section 1 & Section 5 in `GOVERNANCE.md`: Mandate that every single plan execution must spawn both Builder AND Auditor subagents before Coordinator triggers commit.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit.
- **Builder (Subagent)**: Update `smart_commit.sh`, `GOVERNANCE.md`, and `GEMINI.md`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit the shell script and governance update, verify math/logic, and generate auditor handshake.
