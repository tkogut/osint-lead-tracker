#!/bin/bash
# ==============================================================================
# AGENTS-OS v5.0 — Devcontainer / Codespaces Bootstrap
# Automatically run by postCreateCommand in devcontainer.json
# ==============================================================================
set -e

echo "🛸 Configuring AGENTS-OS v5.0 in Devcontainer environment..."

# --------------------------------------------------------------------------- #
# 1. Python venv + dependencies
# --------------------------------------------------------------------------- #
echo "🐍 Configuring Python environment..."
python3 -m venv "$HOME/.antigravity/venv" 2>/dev/null || true
"$HOME/.antigravity/venv/bin/pip" install --upgrade pip --quiet
"$HOME/.antigravity/venv/bin/pip" install GitPython PyGithub --quiet
echo "   ✅ Python venv ready: ~/.antigravity/venv"

# --------------------------------------------------------------------------- #
# 2. Copying Vault (project templates)
# --------------------------------------------------------------------------- #
AGY_DIR="$HOME/.antigravity"
VAULT_DIR="$AGY_DIR/templates/v5.0-swarm"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🛡️ Copying project templates (Vault)..."
mkdir -p "$VAULT_DIR"
cp -ra "$PROJECT_ROOT/vault/." "$VAULT_DIR/"
echo "   ✅ Vault copied to: $VAULT_DIR"

# --------------------------------------------------------------------------- #
# 3. Global skills
# --------------------------------------------------------------------------- #
echo "🧠 Installing global skills..."
for skill_dir in "$PROJECT_ROOT/global_skills"/*/; do
    skill_name=$(basename "$skill_dir")
    mkdir -p "$AGY_DIR/skills/$skill_name"
    cp -ra "$skill_dir." "$AGY_DIR/skills/$skill_name/"
done
echo "   ✅ Skills installed"

# --------------------------------------------------------------------------- #
# 4. Pre-commit security hook
# --------------------------------------------------------------------------- #
if [ -f "$PROJECT_ROOT/hooks/pre-commit" ] && [ -d "$PROJECT_ROOT/.git/hooks" ]; then
    cp "$PROJECT_ROOT/hooks/pre-commit" "$PROJECT_ROOT/.git/hooks/pre-commit"
    chmod +x "$PROJECT_ROOT/.git/hooks/pre-commit"
    echo "   ✅ Pre-commit security hook installed"
fi

# --------------------------------------------------------------------------- #
# 5. Shell config (os-init, os-add-skill as functions)
# --------------------------------------------------------------------------- #
echo "⚙️ Configuring shell commands..."
mkdir -p "$HOME/.bashrc.d"
cat > "$HOME/.bashrc.d/antigravity" <<'SHELLEOF'
# AGENTS-OS v5.0 — shell integration (devcontainer)
export PATH="$HOME/.local/bin:$HOME/.antigravity/venv/bin:$PATH"

os-init() {
    local AGENTS_OS_SCRIPT
    AGENTS_OS_SCRIPT="$(find /workspaces -name 'os-init' -maxdepth 3 2>/dev/null | head -1)"
    if [ -z "$AGENTS_OS_SCRIPT" ]; then
        echo "❌ os-init not found in /workspaces"
        return 1
    fi
    bash "$AGENTS_OS_SCRIPT" "$@"
    if [ -n "$OS_INIT_PROJECT_DIR" ]; then
        cd "$OS_INIT_PROJECT_DIR"
    fi
}

os-add-skill() {
    local AGENTS_OS_SCRIPT
    AGENTS_OS_SCRIPT="$(find /workspaces -name 'os-add-skill' -maxdepth 3 2>/dev/null | head -1)"
    if [ -z "$AGENTS_OS_SCRIPT" ]; then
        echo "❌ os-add-skill not found in /workspaces"
        return 1
    fi
    python3 "$AGENTS_OS_SCRIPT" "$@"
}
SHELLEOF

# Load into current session
echo 'source "$HOME/.bashrc.d/antigravity"' >> "$HOME/.bashrc" 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ AGENTS-OS v5.0 Devcontainer READY"
echo ""
echo "  Available commands:"
echo "    os-init <project-name>   — Create a new Swarm project"
echo "    os-add-skill <skill>     — Add a skill to the project"
echo ""
echo "  🔑 Log in to GitHub: gh auth login"
echo "═══════════════════════════════════════════════════════"
