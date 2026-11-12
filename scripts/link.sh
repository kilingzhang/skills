#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"

TARGET_DIRS=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.codex/skills"
  "$HOME/.gemini/skills"
)

# Also link into T3 Code Antigravity provider skill directories if present
if [[ -d "$HOME/.t3/userdata/providers/antigravity" ]]; then
  for provider_dir in "$HOME/.t3/userdata/providers/antigravity"/*; do
    if [[ -d "$provider_dir" ]]; then
      TARGET_DIRS+=("$provider_dir/config/skills")
    fi
  done
fi

filter_skill="${1:-}"

if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "No skills/ directory found at $SKILLS_SRC" >&2
  exit 1
fi

linked_count=0

for skill_path in "$SKILLS_SRC"/*; do
  [[ -d "$skill_path" ]] || continue
  [[ -f "$skill_path/SKILL.md" ]] || continue

  skill_name="$(basename "$skill_path")"
  if [[ -n "$filter_skill" && "$skill_name" != "$filter_skill" ]]; then
    continue
  fi

  for target_root in "${TARGET_DIRS[@]}"; do
    mkdir -p "$target_root"
    dest="$target_root/$skill_name"

    # Replace existing directory or symlink pointing elsewhere cleanly
    if [[ -L "$dest" || ! -e "$dest" ]]; then
      ln -sfn "$skill_path" "$dest"
    elif [[ -d "$dest" ]]; then
      rm -rf "$dest"
      ln -sfn "$skill_path" "$dest"
    fi
  done

  echo "✓ Linked skill: $skill_name"
  linked_count=$((linked_count + 1))
done

if [[ "$linked_count" -eq 0 ]]; then
  echo "No matching skills found to link." >&2
  exit 1
fi

echo "Done! Linked $linked_count skill(s) across ${#TARGET_DIRS[@]} agent directories."
