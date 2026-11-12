# skills

Personal collection of reusable AI coding agent skills by [@kilingzhang](https://github.com/kilingzhang), compatible with **Claude Code**, **Codex**, **Gemini CLI**, **Cursor**, and the open [`npx skills`](https://skills.sh) ecosystem.

---

## Included Skills

| Skill | Summary | Path |
| :--- | :--- | :--- |
| [`intent-spec`](./skills/intent-spec/SKILL.md) | Turn rough ideas into structured specs engineered for **Intention Group Review**—calibrating `Why`, orthogonal `Intention Groups`, `Impact`, and `Non-Goals` across `L1 / L2 / L3` complexity tiers before saving a spec or implementing atomic changes. | `skills/intent-spec` |
| [`context-slim`](./skills/context-slim/SKILL.md) | Audit, relocate, compress, and verify project agent context (`AGENTS.md`, `CLAUDE.md`, `.claude/rules`, `docs/`, hooks) and installed skills—backed by deterministic token/glob/transcript-telemetry scripts, blind subagent over-deletion checks, and canary auto-load tests. | `skills/context-slim` |
| [`plain-language`](./skills/plain-language/SKILL.md) | Scan and rewrite Chinese and English corporate jargon, buzzwords, and AI cliches across single or multi-repo workspaces into direct prose while protecting code identifiers, test assertions, and frozen files. | `skills/plain-language` |

---

## Installation & Updates

Install or sync via the [Skills CLI](https://skills.sh):

```bash
# Interactive selection from this repository
npx skills add kilingzhang/skills

# Install a specific skill
npx skills add kilingzhang/skills --skill intent-spec
npx skills add kilingzhang/skills --skill context-slim
npx skills add kilingzhang/skills --skill plain-language

# Update installed skills
npx skills update
```

---

## Repository Layout

```text
skills/
└── skills/
    └── <skill-name>/
        ├── SKILL.md     # Core skill instructions & YAML trigger metadata
        ├── agents/      # Optional UI metadata (e.g. openai.yaml)
        ├── references/  # Optional examples, schemas, or deep-dive docs
        └── scripts/     # Optional skill-bundled helper scripts
```

## License

[MIT](./LICENSE)
