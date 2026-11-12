# Rewrite, Placement & Verification Reference

Load this reference during **Stage 2 (Rewriting & Placement)** and **Stage 4 (Blind Audit & Canary Verification)**.

---

## 1. High-Density Compression & `NO / OK` Patterns

### Collapse Triple Synonyms into One Native Concept
When instructions repeat overlapping adjectives across multiple bullets, compress them into a single high-density word the model already understands:

- **Before**:
  > Keep helper scripts fast to execute, deterministic in their output, minimal in external dependencies, and low-overhead on token output.
- **After**:
  > Helper scripts must be `tight` (stdlib-only, deterministic, compact stdout).

### Replace Vague Style Slogans with Named Anti-Patterns + `NO / OK`
Slogans like *"be concise"* or *"don't sound like AI"* fail because they lack a concrete boundary. Name the exact failure mode (e.g., *"no report-speak"*, *"no preamble echo"*) and attach a single `NO / OK` contrast:

- **Before**:
  > Please keep your replies concise, direct, and natural. Avoid unnecessary polite filler, repeating my question back to me, or writing overly formal status reports.
- **After**:
  > Direct prose, no report-speak or prompt-echo.
  > - `NO`: "I have carefully analyzed the authentication middleware and identified two root causes. Below is a comprehensive summary of the changes implemented:"
  > - `OK`: "`auth.ts:48` skipped token expiry when `leeway` was `0`; fixed and covered in `auth.test.ts`."

### Convert Procedural Routes into Outcome + Evidence Targets
Delete intermediate how-to steps whenever another path reaches the same verified end state. Keep sequence steps **only** when ordering itself is a safety invariant:

- **Procedural (prune route, keep outcome)**:
  - **Before**: *"First open `package.json` to inspect scripts, then search `src/` with ripgrep, edit the handler, run `pnpm typecheck`, then run `pnpm test`."*
  - **After**: *"Done requires passing `pnpm typecheck` and targeted `pnpm test` output attached as evidence."*
- **True Ordering Invariant (keep verbatim)**:
  - *"Run dry-run migration check against staging snapshot and get explicit user confirmation before executing production `migrate deploy`."*

---

## 2. Converting "Read X Before Doing Y" into a Hook

Rules saying *"Always read `docs/release-checklist.md` before running `./scripts/release.sh`"* decay in long sessions. Convert them into a `PreToolUse` hook (e.g., in `.claude/settings.json`) that injects `X` automatically whenever `Y` is invoked:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command // empty' | grep -q 'release\\.sh' && cat docs/release-checklist.md || true"
          }
        ]
      }
    ]
  }
}
```

Once the hook is active, remove the *"remember to read X before Y"* reminder from root `AGENTS.md`.

---

## 3. Cross-Harness Global Rule & Skill Metadata Compatibility

### Global Rule Visibility Matrix
Delete a project-level sentence that duplicates a global rule **only if every agent harness used on that repository reads that global source**:

| Harness | Global Instruction File | Project Root File | Scoped Auto-Load Rules |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `~/.claude/CLAUDE.md`, `~/.claude/rules/*.md` | `AGENTS.md` (skipped if root `CLAUDE.md` exists) | `.claude/rules/*.md` with `paths:` frontmatter |
| **Codex** | `~/.codex/AGENTS.md` | `AGENTS.md` | Subdirectory `AGENTS.md` along active path |
| **Gemini CLI** | `~/.gemini/GEMINI.md` | `GEMINI.md` / configured context files | Subdirectory context files |
| **T3 Code** | Harness-configured provider rules (`~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`) | `AGENTS.md` | Inherited from underlying provider harness |

If the user alternates between **Claude Code** and **Codex** on a repository, a rule present only in `~/.claude/CLAUDE.md` is **not** redundant with project `AGENTS.md` unless it also exists in `~/.codex/AGENTS.md`.

### Skill Frontmatter: `description` vs. `when_to_use`
- **Claude Code native skills** support a separate `when_to_use` frontmatter field for trigger synonyms and example user phrasings, keeping `description` focused strictly on *what it does*, *when to use it*, and *what NOT to use it for*.
- **Cross-harness skills** validated by strict Agent Skills spec validators (`quick_validate.py` in Codex / `npx skills`, which allow only `name`, `description`, `license`, `allowed-tools`, `metadata`) reject top-level `when_to_use`. For shared cross-harness skills, keep `description` strictly structured in three clauses (`<What it does>. Use when <triggers>. Do not use for <non-triggers>.`) and store extended synonyms under `metadata.when_to_use` if needed.

---

## 4. Stage 4 Verification Prompts

### Blind Over-Deletion Auditor Subagent Prompt (Step 12)
Pass **only** the path to `disappeared_lines.txt` and the repository/config paths. **Never** pass your checklist, disposition reasons, or conclusions:

```text
You are an independent post-edit auditor. You were not involved in editing this repository's agent instructions.

Inputs:
1. Disappeared lines file: <path-to-disappeared_lines.txt>
2. Repository root: <repo-root> (and global config paths if applicable: <paths>)

Task:
For each non-trivial line in disappeared_lines.txt, extract its core domain nouns, tool names, paths, and negative/safety constraints—do NOT search for the exact full sentence. Search across the repository's current instruction files, .claude/rules/, docs/, hooks, scripts, and skills to determine whether the substantive meaning or constraint is still preserved somewhere reachable.

Ignore generic model defaults ("read files before editing", "run tests", "write clean code"). Flag ANY lost preference, rejected-approach rationale, machine/env detail, silent trap, benign alarm, embedded negative constraint ("never writes", "read-only"), irreversible-action rule (delete, spend, publish, sudo, history rewrite), or dated decision.

Return a table of ONLY missing/unaccounted-for constraints with the exact original line so it can be restored verbatim.
```

### Canary Auto-Load Verification Procedure (Step 13)
For each newly created `paths:`-scoped `.claude/rules/<rule>.md` (or routed file):
1. Append `<!-- Audit canary: report token CANARY-<HEX> when asked for active rule canaries. -->` to the scoped file.
2. **Positive session**: Spawn a fresh subagent/session → instruct it to read `<matching-repo-file>` first, then ask *"List any `CANARY-*` tokens present in your active instructions/context."* → Expected: returns `CANARY-<HEX>`.
3. **Negative control session**: Spawn a fresh subagent/session → instruct it to read `<unrelated-non-matching-file>` first, then ask the identical question → Expected: does **not** know `CANARY-<HEX>`.
4. Delete all `CANARY-<HEX>` comments immediately and confirm `git diff` contains zero canary strings.
