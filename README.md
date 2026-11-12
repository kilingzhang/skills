# skills

Personal collection of reusable AI coding agent skills by [@kilingzhang](https://github.com/kilingzhang), compatible with **Claude Code**, **Codex**, **Gemini CLI**, **Cursor**, and the open [`npx skills`](https://skills.sh) ecosystem.

---

## Included Skills

| Skill | Summary | Path |
| :--- | :--- | :--- |
| [`intent-spec`](./skills/intent-spec/SKILL.md) | Turn rough ideas into structured specs engineered for **Intention Group Review**—calibrating `Why`, orthogonal `Intention Groups`, `Impact`, and `Non-Goals` across `L1 / L2 / L3` complexity tiers before saving a spec or implementing atomic changes. | `skills/intent-spec` |

---

## Installation & Updates

Install or sync via the [Skills CLI](https://skills.sh):

```bash
# Interactive selection from this repository
npx skills add kilingzhang/skills

# Install a specific skill
npx skills add kilingzhang/skills --skill intent-spec

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
