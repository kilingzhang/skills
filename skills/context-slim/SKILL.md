---
name: context-slim
description: |
  Audit, relocate, compress, and verify project agent instructions (AGENTS.md, CLAUDE.md, .claude/rules, docs, hooks) and installed skills to cut always-loaded context without losing hard constraints. Use when the user asks to slim, prune, audit, deduplicate, or reorganize agent context, instruction files, rules, or installed skills, or to re-baseline context after a model upgrade. Do not use for summarizing live chat history, compacting an active conversation window, or editing application code unrelated to agent configuration.
---

# Context Slim — Agent Context & Skills Audit Workflow

## Goal

Shrink every-turn agent context to high-signal rules while preserving 100% of user preferences, domain traps, and irreversible-action rules. Most bloated context is **misplaced** (on-demand material sitting in always-loaded files) rather than over-explained.

Match the user's language in all tables, questions, and reports.

---

## Hard Gate: Inventory & Checklist Before Touching Disk

**Completion state of Stage 1–2**: A measured context inventory and a five-action disposition table approved by the user.
**Constraint**: Never create, edit, move, or delete any repository file, global rule, hook, or skill before explicit user sign-off on the checklist.

---

## Stage 1: Measure Inventory & Real Skill Usage

Run the bundled deterministic audit script first (prefer script output over manual estimation):

```bash
python3 <skill-dir>/scripts/audit_context.py inventory --repo <repo-root>
python3 <skill-dir>/scripts/audit_context.py skill-usage --repo <repo-root>
```

1. **Audit Every-Turn (Always-Loaded) Context First**:
   - Root `AGENTS.md` / `CLAUDE.md` (including `@path` transcluded files).
   - Global rules (`~/.claude/CLAUDE.md`, unscoped `~/.claude/rules/*.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`).
   - Project `.claude/rules/*.md` **without** `paths:` frontmatter.
   - Every installed project and global skill's `description` (and `when_to_use`).
   - Report character/word counts and share of total every-turn load for each item.
2. **Audit On-Demand Context Second**:
   - `paths:`-scoped `.claude/rules/*.md`, subdirectory `AGENTS.md`, `SKILL.md` bodies, `references/`, and linked `docs/`.
   - Identify every-turn sections that actually belong in an on-demand tier.
3. **Judge Skill Usage from Real Invocation Logs Only**:
   - Use actual session transcripts (tool calls reading `SKILL.md` or invoking `Skill`, and user `/skill` or `$skill` commands), **never** repository `grep` or system-prompt `skill_listing` / `session_meta` blocks.
   - List 0-use or stale skills in the disposition table for user confirmation before removal.

---

## Stage 2: Build the Five-Action Disposition Table

Evaluate every section, rule, and skill, then present a single checklist table for user confirmation:

| Source File & Section | Chars | Action (`Fix` / `Delete` / `Move` / `Rewrite` / `Keep`) | Destination (if `Move`) | One-Sentence Reason |
| :--- | :--- | :--- | :--- | :--- |

### Triage Rules

1. **Protected Content — Never Delete**:
   - User preferences, rejected approaches **and why they were rejected**, and machine/environment facts.
   - **Silent traps** (failure modes that do not throw errors) and **benign alarms** (outputs that look like errors but are normal).
   - Embedded half-sentence negative constraints (e.g., *"never writes to..."*, *"does not upload..."*).
   - Explicit rules for **irreversible, costly, or privileged actions**: deleting data, spending money, publishing/releasing, privilege escalation (`sudo`), rewriting pushed git history.
   - **Dated decisions** (explicit sign-offs with timestamps/dates).

2. **Counterfactual Behavioral-Delta Test**:
   - Ask sentence by sentence: *"If this line is deleted, will my behavior actually change?"*
   - Delete baseline model priors ("read files before editing", "run tests", "handle edge cases", "write maintainable code").
   - If uncertain whether behavior changes, mark `Keep (confirm)` and ask the user.

3. **Target State & Evidence Over Procedural Routes**:
   - State what "done" looks like, acceptance criteria, and required verification evidence instead of step-by-step how-to instructions.
   - If deleting a step still allows reaching the same outcome via another valid path, delete that step.
   - Keep sequence instructions **only** when order itself is the constraint (e.g., *verify before release*, *confirm before delete*).

4. **High-Density Terms & `NO / OK` Contrast Pairs**:
   - Collapse repeated requirements into one native term the model already knows (e.g., replace *"fast, deterministic, low-overhead"* with `tight`).
   - Replace vague style slogans (*"be concise"*) with named anti-patterns (*"no report-speak"*) plus a `NO / OK` example pair. See [references/rewrite-and-verification-patterns.md](references/rewrite-and-verification-patterns.md).

5. **Put Every Rule in Its Right Mechanism**:
   - Requires judgment / branching workflow → **Skill** (`SKILL.md`).
   - Deterministic (same input always yields same output) → **Script or Hook**.
   - *"Read X before doing Y"* → **Hook** that injects `X` automatically when `Y` runs.
   - Project commands & release steps → **Project guide** (`AGENTS.md` or `docs/`).
   - Cross-project hard invariants → **Global rules**. Delete project duplicates **only** when every agent tool the user runs on this project reads that global rule file.
   - Unpredictably triggered mid-chat rules (**commit, release, reply tone, delete**) → Keep in **root `AGENTS.md`**.
   - Material moved to `docs/` → Leave a **one-line trigger pointer** in root `AGENTS.md` stating *when* to read it.
   - **No root `CLAUDE.md`**: Never create a root `CLAUDE.md`—it causes Claude Code to stop reading `AGENTS.md`. If both exist, propose consolidating into `AGENTS.md` under `Fix`.
   - **Skill structure**: `description` states only *what it does*, *when to use it*, and *what NOT to use it for*. Move trigger synonyms to `when_to_use` (where supported by the harness) and scenario-specific branches to `references/`.

---

## Stage 3: Two-Phase Execution (After User Confirmation)

Take a baseline snapshot before editing:

```bash
python3 <skill-dir>/scripts/audit_context.py snapshot --repo <repo-root> --out <scratch-dir>/pre-slim-snapshot
```

Execute strictly in two separate passes—**never move and rewrite at the same time**:

1. **Pass 1 — Move Verbatim**:
   - Relocate approved `Move` lines and blocks word-for-word to their target files (`paths:` rules, `docs/`, `references/`, scripts/hooks).
   - **Irreversible-action rules must always move verbatim as whole blocks—never compress or paraphrase them.**
2. **Pass 2 — Compress & Clean**:
   - Apply approved `Fix`, `Delete`, and `Rewrite` edits only after Pass 1 relocations are in place.

---

## Stage 4: Four-Layer Post-Edit Verification

Completion requires passing all four checks with evidence:

1. **Self-Verification (`audit_context.py verify`)**:
   ```bash
   python3 <skill-dir>/scripts/audit_context.py verify --repo <repo-root> --snapshot <scratch-dir>/pre-slim-snapshot
   ```
   - Every glob in `paths:` frontmatter must match at least one real file in the repository.
   - `grep` across the repo and configs for split/deleted old filenames to confirm zero dangling references.
   - Reconcile **every disappeared line** in `disappeared_lines.txt` against user-approved `Delete` or `Rewrite` items in the checklist.

2. **Blind Subagent Over-Deletion Audit**:
   - Spawn a fresh read-only subagent that **did not participate** in the slimming pass.
   - Pass **only** `disappeared_lines.txt` and read access to the repository/config directories—**withhold your checklist, reasons, and conclusions**.
   - Instruct it to search by **key domain nouns and identifiers** (never full verbatim sentences) using the prompt in [references/rewrite-and-verification-patterns.md](references/rewrite-and-verification-patterns.md).
   - Restore verbatim any constraint whose meaning can no longer be found anywhere.

3. **Canary Verification for On-Demand Loading**:
   - Plant a temporary unique canary token (e.g., `CANARY-7D2K`) inside each newly created on-demand file.
   - **Positive test**: Start a fresh session/subagent, read a file matching the rule's `paths:` (or trigger condition), then ask for the canary—must return the token.
   - **Negative control**: Start a second fresh session/subagent, read an unrelated non-matching file, then ask for the canary—must confirm the file was not preloaded.
   - Remove all canary tokens immediately after testing and verify a clean diff.

4. **Distill Reusable Model-Upgrade Baseline**:
   - Summarize before/after every-turn character counts, relocated paths/hooks, and which surviving rules compensate for current model blind spots, saving a short audit receipt (e.g., `docs/context-slim-baseline.md` if requested) so the user can re-run this skill cleanly whenever a newer model ships.
