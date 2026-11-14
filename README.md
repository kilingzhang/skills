# skills

Personal collection of reusable AI coding agent skills by [@kilingzhang](https://github.com/kilingzhang), compatible with **Claude Code**, **Codex**, **Gemini CLI**, **Cursor**, and the [`npx skills`](https://skills.sh) ecosystem.

---

## First-Party Skills

Maintained directly in this repository under `skills/`:

| Skill | Summary | Path |
| :--- | :--- | :--- |
| [`intent-spec`](./skills/intent-spec/SKILL.md) | Turn rough ideas into structured specs engineered for **Intention Group Review**—calibrating `Why`, orthogonal `Intention Groups`, `Impact`, and `Non-Goals` across `L1 / L2 / L3` complexity tiers before saving a spec or implementing atomic changes. | `skills/intent-spec` |
| [`context-slim`](./skills/context-slim/SKILL.md) | Audit, relocate, compress, and verify project agent context (`AGENTS.md`, `CLAUDE.md`, `.claude/rules`, `docs/`, hooks) and installed skills—backed by deterministic token/glob/transcript-telemetry scripts, blind subagent over-deletion checks, and canary auto-load tests. | `skills/context-slim` |
| [`plain-language`](./skills/plain-language/SKILL.md) | Scan and rewrite Chinese and English corporate jargon, buzzwords, and AI cliches across single or multi-repo workspaces into direct prose while protecting code identifiers, test assertions, and frozen files. | `skills/plain-language` |

---

## Referenced Upstream Skills

Declared in [`remote-skills.json`](./remote-skills.json) **without copying or forking upstream files**. Installing them points [`skills`](https://skills.sh) directly at each author's repository so `npx skills update` pulls upstream changes straight from the source.

| Skill | Summary | Upstream |
| :--- | :--- | :--- |
| [`kubai-icons`](https://icons.kubai.design/skill/) | Draw layered functional icons as animated hover SVG+JS or static SVG files in the Kubai Icons style. | [`kubai087/kubai-icons`](https://github.com/kubai087/kubai-icons) |
| [`aiforui` (`*`)](https://aiforui.dev/skills) | UI design engineering, animation, gestures, mobile polish, and interface review skills by Emil Kowalski. | [`emilkowalski/skills`](https://github.com/emilkowalski/skills) |

---

## Installation & Updates

### Install everything (first-party + upstream references)

```bash
npx github:kilingzhang/skills
```

This installs first-party skills from `kilingzhang/skills` and installs each entry in [`remote-skills.json`](./remote-skills.json) directly from its upstream repository via `npx skills add`.

Useful options:

```bash
# Preview the exact npx skills add commands
npx github:kilingzhang/skills --dry-run

# List configured first-party and upstream skills
npx github:kilingzhang/skills --list

# Install only referenced upstream skills (or only first-party skills)
npx github:kilingzhang/skills --remote-only
npx github:kilingzhang/skills --local-only

# Install a single skill by name into the current project instead of globally
npx github:kilingzhang/skills -p -s kubai-icons
```

### Install individual skills directly with `npx skills`

```bash
# First-party skills from this repository
npx skills add kilingzhang/skills -g

# Referenced upstream skill straight from its author repository
npx skills add kubai087/kubai-icons --skill kubai-icons -g
npx skills add emilkowalski/skills -g
```

### Update installed skills

```bash
# Pulls each skill directly from its recorded upstream repository
npx skills update
```

---

## Adding a New Upstream Skill

Add an entry to [`remote-skills.json`](./remote-skills.json):

```json
{
  "source": "owner/repo",
  "skills": ["skill-name"],
  "homepage": "https://example.com",
  "description": "Short summary of what the skill does."
}
```

Omit `skills` (or set `["*"]`) to install all skills exposed by that upstream repository, and optionally add `"ref": "branch-or-tag"` to pin a specific ref.

---

## Repository Layout

```text
skills/
├── bin/
│   └── sync-skills.mjs      # Thin wrapper calling npx skills add per source
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md         # Core skill instructions & YAML trigger metadata
│       ├── agents/          # Optional UI metadata (e.g. openai.yaml)
│       ├── references/      # Optional examples, schemas, or deep-dive docs
│       └── scripts/         # Optional skill-bundled helper scripts
├── package.json             # Enables `npx github:kilingzhang/skills`
└── remote-skills.json       # Upstream third-party skill references
```

## License

First-party skills and scripts in this repository are licensed under the [MIT License](./LICENSE). Referenced upstream skills in [`remote-skills.json`](./remote-skills.json) are neither included in nor relicensed by this repository and remain subject to their respective upstream licenses.
