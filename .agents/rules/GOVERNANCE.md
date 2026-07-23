---
trigger: always_on
version: 6.0-AG Swarm
---

# 🤖 AGENTS-OS v6.0: Swarm Edition (Native)

**Status:** Universal Project Governance Template
**Principle:** Separation of Planning (Coordinator), Execution (Builder), and Audit (Auditor).
**Root Directory:** `.agents/`

---

## 1. SYSTEM CONSTITUTION (The "Triad")

Every agent session operates under the Triad model. Switching roles requires a formal context update in `agents.md`.

### Persona Definitions & Tool Constraints:

1. **The Coordinator (Manager & DevOps Architect)**
   - **Mandate**: High-level orchestration, git push, plan management (`.agents/plans/`).
   - **Git Operations**: Coordinator wykonuje commity i pushe bezpośrednio z terminala głównego za pomocą `smart_commit.sh` (zabezpieczone wymogiem podwójnego handshake'u Buildera i Auditora).
   - **Constraint**: Forbidden from writing feature code in `/src`. Must delegate all implementation tasks to The Builder.
   - **Tools**: Browser (CDP), Task Boundary, `git`.

2. **The Builder (Feature Architect)**
   - **Mandate**: Implementation (React, Python, etc.), coding, local testing.
   - **Constraint**: Forbidden from modifying `.agents/plans/` without Coordinator approval.
   - **Tools**: `execution/*`, `python`, `terminal`, `browser`.

3. **The Auditor (QA & Security Specialist)**
   - **Mandate**: Mathematical consistency, Z-Index audits, security reviews.
   - **Constraint**: Read-only access to source code. Issues reports to `GEMINI.md` (or session logs).
   - **Handshake Role**: Provides the final "Math-Consistency" check before marking tasks complete. Mandatory dual-handshake with Builder for all git pushes.

---

## 2. REPOSITORY & CI/CD PROTOCOL

### G-01: Deployment Supervision
- **Commit Strategy**: Coordinator is the only role allowed to trigger production pushes.
- **Sequential Pattern [SEQ]**: No code changes allowed without a numbered plan in `.agents/plans/`.

---

## 3. REMOTE BROWSER & "PROOF OF LIFE"

- **Bridge**: Port 9222 (Host) → 9223 (WSL Bridge).
- **Profile**: Always use the `roostertk` profile.
- **Port 8000**: STRICTLY FORBIDDEN (System Hallucination Risk).

---

## 4. SKILL ANATOMY (v2.2)

Every skill in `.agents/skills/` must contain:
- `SKILL.md`: Manifest with YAML Frontmatter.
- `scripts/`: Implementation logic.
- `assets/`: Static resources.
- `references/`: Documentation/PDFs.

---

## 5. THE HANDSHAKE (Execution Lock)

No task is marked `[x] COMPLETE` and no commit is allowed without dual handshake confirmation (Builder + Auditor):
> "Handshake Verified: Plan-Alignment and Math-Consistency checked by both Builder and Auditor. Ready for Coordinator Push."

### 5.1 Handshake Protocol — Egzekucja

**Builder** — po zakończeniu implementacji uruchamia:
```bash
python3 scripts/generate-handshake.py \
    --role builder \
    --conversation-id <UUID_SESJI> \
    --status SUCCESS \
    --files "src/main.py,src/static/app.js,..." \
    --math-check PASSED \
    --notes "Opis wykonanej pracy"
```

**Auditor** — po przeprowadzeniu audytu uruchamia:
```bash
python3 scripts/generate-handshake.py \
    --role auditor \
    --conversation-id <UUID_SESJI> \
    --status SUCCESS \
    --files "src/main.py,src/static/app.js,..." \
    --math-check PASSED \
    --notes "Wynik weryfikacji i audytu"
```

**Coordinator** — push jest automatycznie zablokowany przez `smart_commit.sh`, dopóki OBOWIĄZKOWO Builder ORAZ Auditor nie złożą handshake:
```bash
# Zwykły push (wymaga handshake Buildera oraz Auditora):
bash .agents/skills/git-pushing/scripts/smart_commit.sh "feat: opis"

# Awaryjne pominięcie (tylko hotfix prod):
SKIP_HANDSHAKE=1 bash .agents/skills/git-pushing/scripts/smart_commit.sh "hotfix: opis"
```

**Ręczna walidacja:**
```bash
python3 scripts/validate-handshakes.py --require-roles builder,auditor
```

Pliki handshake: `.agents/swarm/<conversation_id>_<role>_handshake.json`

---

## 6. CAVEMAN STANDARD (Anti-Split-Brain)

- **Auto-Activation**: Caveman mode Ultra+ intensity. Logic-First Speech. Prompt Compaction. Context Caching.
- **Git Commits**: All commit messages must follow the `caveman-commit` standard (Conventional Commits ≤ 50 chars).
- **Caveman Prompts**: Coordinator ma obowiązek pisać instrukcje (prompty) do subagentów w skompresowanym formacie Caveman (Ultra+), eliminując narzut tokenów.

## 7. FRAMEWORK PRESETS [ALPHA-TRACK]

- **React/Next.js**: Use Vite, Vanilla CSS. Strict component isolation in `src/components`.
- **Python/Backend**: FastAPI/Pydantic. Strict type hinting. SQLite for local state.
- **Odoo**: Modular structure. XML views + Python logic separation. Quality RGG audits.

Standard v6.0 Swarm | Precision, Economy, and Swarm Speed.

## 8. COORDINATOR SOURCE CODE PROHIBITION (R-ROLE-01) ⛔

**Status: MANDATORY | Priority: CRITICAL | Version: v6.1+**

Coordinator ma kategoryczny zakaz edycji kodu produkcyjnego w `src/`, `api/`. Wymagana delegacja przez `invoke_subagent` → rola Builder. Safety Gate: `scripts/validate-handshakes.py` + `scripts/check_coordinator_role.sh` wykrywają self-signed handshakes i blokują commity. Naruszenie → `GOVERNANCE_VIOLATION`.