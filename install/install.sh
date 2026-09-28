#!/usr/bin/env bash
# Install Yiğit Investment Copilot for Claude Code, Codex / ChatGPT desktop and/or OpenCode (macOS / Linux).
#   bash install/install.sh --claude --opencode-extras
#   bash install/install.sh --codex
#   bash install/install.sh --opencode
# --claude           skill into ~/.claude/skills + slash commands into ~/.claude/commands
#                    (alternative: claude plugin marketplace add yigityildiz0/yigit-investment-copilot)
# --opencode         skill + agent + commands into ~/.config/opencode
# --opencode-extras  only agent + commands (skill already in ~/.claude/skills or ~/.agents/skills)
# Existing installs (and same-name command files) are moved to <name>.bak-<timestamp>; nothing is deleted.
set -euo pipefail
NAME="yigit-investment-copilot"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/skill/$NAME"
[ -f "$SRC/SKILL.md" ] || { echo "Skill folder not found: $SRC" >&2; exit 1; }
CLAUDE=0; CODEX=0; OPENCODE=0; EXTRAS=0
for arg in "$@"; do
  case "$arg" in
    --claude) CLAUDE=1 ;;
    --codex) CODEX=1 ;;
    --opencode) OPENCODE=1 ;;
    --opencode-extras) EXTRAS=1 ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done
if [ $((CLAUDE + CODEX + OPENCODE + EXTRAS)) -eq 0 ]; then
  echo "Choose at least one target: --claude --codex --opencode --opencode-extras"; exit 1
fi
STAMP="$(date +%Y%m%d-%H%M%S)"
install_skill() {
  local target_root="$1" dst="$1/$NAME"
  mkdir -p "$target_root"
  if [ -e "$dst" ]; then mv "$dst" "$dst.bak-$STAMP"; echo "backup  -> $dst.bak-$STAMP"; fi
  cp -R "$SRC" "$dst"
  echo "skill   -> $dst"
}
install_files() {
  local from="$1" to="$2"
  mkdir -p "$to"
  for f in "$from"/*.md; do
    local dst="$to/$(basename "$f")"
    if [ -e "$dst" ]; then
      cmp -s "$f" "$dst" && continue
      mv "$dst" "$dst.bak-$STAMP"
    fi
    cp "$f" "$dst"
  done
}
if [ $CLAUDE -eq 1 ]; then
  install_skill "$HOME/.claude/skills"
  install_files "$ROOT/platforms/claude/commands" "$HOME/.claude/commands"
  echo "claude commands -> $HOME/.claude/commands (/borsa-tara, /hisse-analiz, /sabah-bulteni ...)"
fi
[ $CODEX -eq 1 ] && install_skill "$HOME/.agents/skills"
[ $OPENCODE -eq 1 ] && install_skill "$HOME/.config/opencode/skills"
if [ $OPENCODE -eq 1 ] || [ $EXTRAS -eq 1 ]; then
  install_files "$ROOT/platforms/opencode/agents" "$HOME/.config/opencode/agents"
  install_files "$ROOT/platforms/opencode/commands" "$HOME/.config/opencode/commands"
  echo "opencode agent + commands -> $HOME/.config/opencode"
fi
if [ $OPENCODE -eq 1 ] && [ $((CLAUDE + CODEX)) -gt 0 ]; then
  echo "WARNING: OpenCode also reads ~/.claude/skills and ~/.agents/skills; prefer --opencode-extras with Claude Code or Codex." >&2
fi
command -v python3 >/dev/null 2>&1 || echo "WARNING: python3 (3.9+) not found; the data scripts need it." >&2
echo "Done. Restart the app(s) and ask, e.g.: 'Piyasa ne durumda?'"
