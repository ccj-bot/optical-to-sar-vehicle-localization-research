#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="/mnt/d/profile/research/workspace"
PROMPT_FILE="${1:-}"

if [ -z "$PROMPT_FILE" ]; then
  echo "Usage: run_codex_readonly.sh /path/to/prompt.txt"
  exit 1
fi

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Prompt file not found: $PROMPT_FILE"
  exit 1
fi

mkdir -p "$WORKSPACE/00_project_control/codex_runs"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$WORKSPACE/00_project_control/codex_runs/codex_readonly_${STAMP}.md"
LOG="$WORKSPACE/00_project_control/codex_runs/codex_readonly_${STAMP}.log"

cd "$WORKSPACE"

echo "Codex read-only run" > "$LOG"
echo "Timestamp: $STAMP" >> "$LOG"
echo "Workspace: $WORKSPACE" >> "$LOG"
echo "Prompt: $PROMPT_FILE" >> "$LOG"
echo "" >> "$LOG"

codex exec \
  --cd "$WORKSPACE" \
  --skip-git-repo-check \
  --sandbox read-only \
  --output-last-message "$OUT" \
  - < "$PROMPT_FILE" 2>&1 | tee -a "$LOG"

echo "" >> "$LOG"
echo "Final message saved to: $OUT" >> "$LOG"

echo "$OUT"
