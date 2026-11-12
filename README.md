# skills

Personal collection of reusable AI coding agent skills by [@kilingzhang](https://github.com/kilingzhang), compatible with **Claude Code**, **Codex**, **Gemini CLI**, **T3 Code**, and the open [`npx skills`](https://skills.sh) ecosystem.

---

## Included Skills

| Skill | Summary | Path |
| :--- | :--- | :--- |
| [`intent-spec`](./skills/intent-spec/SKILL.md) | Turn rough ideas into structured specs engineered for **Intention Group Review**—calibrating `Why`, orthogonal `Intention Groups`, `Impact`, and `Non-Goals` across `L1 / L2 / L3` complexity tiers before saving a spec or implementing atomic changes. | `skills/intent-spec` |

---

## Install on Any Machine (`npx skills`)

Install all skills or pick specific ones via the Skills CLI:

```bash
# Interactive selection from this repository
npx skills add kilingzhang/skills

# Install a single skill directly
npx skills add kilingzhang/skills --skill intent-spec
```

---

## Local Development & Live Symlink Workflow

When maintaining skills locally on your own machine, clone this repository to `~/skills` and run `./scripts/link.sh` so edits under `skills/<name>/` take effect immediately across `~/.agents/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.gemini/skills`, and T3 Code:

```bash
git clone git@github.com:kilingzhang/skills.git ~/skills
cd ~/skills

# Link all skills (or pass a single skill name: ./scripts/link.sh intent-spec)
./scripts/link.sh
```

### Create a New Skill

```bash
./scripts/new-skill.sh my-new-skill "My New Skill"
```

This creates `skills/my-new-skill/SKILL.md` + `agents/openai.yaml` and links it into all local agent directories automatically.

---

## Repository Layout

```text
skills/
├── scripts/
│   ├── link.sh          # Symlink skills/* into local agent directories
│   └── new-skill.sh     # Scaffold a new skill and link it immediately
└── skills/
    └── <skill-name>/
        ├── SKILL.md     # Core skill instructions & YAML trigger metadata
        ├── agents/      # Optional UI metadata (e.g. openai.yaml)
        ├── references/  # Optional examples, schemas, or deep-dive docs
        └── scripts/     # Optional deterministic helper scripts
```

## License

[MIT](./LICENSE)
