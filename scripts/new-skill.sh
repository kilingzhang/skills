#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/new-skill.sh <skill-name> [display-name]" >&2
  exit 1
fi

SKILL_NAME="$1"
DISPLAY_NAME="${2:-$SKILL_NAME}"

if [[ ! "$SKILL_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "Error: skill-name must be kebab-case (lowercase letters, digits, hyphens)." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$REPO_ROOT/skills/$SKILL_NAME"

if [[ -e "$SKILL_DIR" ]]; then
  echo "Error: $SKILL_DIR already exists." >&2
  exit 1
fi

mkdir -p "$SKILL_DIR/agents" "$SKILL_DIR/references"

cat > "$SKILL_DIR/SKILL.md" <<EOF
---
name: $SKILL_NAME
description: |
  TODO: Describe what this skill does and explicitly when it should (and should not) trigger.
---

# $DISPLAY_NAME

## Goal

TODO: State the core objective and why this workflow matters.

## Workflow

1. Step 1...
2. Step 2...
EOF

cat > "$SKILL_DIR/agents/openai.yaml" <<EOF
interface:
  display_name: "$DISPLAY_NAME"
  short_description: "TODO: Short one-line summary"
  default_prompt: "Use \$$SKILL_NAME to ..."
EOF

echo "✓ Created skill scaffold at: $SKILL_DIR"
"$REPO_ROOT/scripts/link.sh" "$SKILL_NAME"
