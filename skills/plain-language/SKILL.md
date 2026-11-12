---
name: plain-language
description: |
  Scan and rewrite Chinese and English corporate jargon, buzzwords, and AI cliches across Git repositories or multi-repo workspaces into clear, direct language while enforcing frozen-file and contract boundaries. Use when the user asks to clean up jargon or buzzwords, run periodic wording hygiene, de-jargon docs, comments, prompts, or UI copy, or invokes plain-language. Do not use for editing archived specs, SQL migrations, generated protobuf/lockfiles, or locked contract artifacts.
---

# Plain Language — Bilingual Jargon & Buzzword Cleanup (ZH + EN)

## References & Deterministic Script

- Bilingual scanner & boundary verifier: [`scripts/scan_jargon.py`](scripts/scan_jargon.py)
- Chinese + English replacement tables & whitelists: [`references/vocabulary.md`](references/vocabulary.md)

## Mode Routing (Pick Scope First; Default to Periodic Incremental)

| Scenario | Command | Behavior |
| :--- | :--- | :--- |
| **Periodic incremental cleanup (default)** | `python3 <skill-dir>/scripts/scan_jargon.py scan --root <workspace> --since 14.days` | Scans lines added/modified within the last 14 days that still exist across discovered Git repo(s) (supports `7.days`, `30.days`, or a git rev; add `--whole-file` to scan entire touched files) |
| **Local uncommitted diff check** | `python3 <skill-dir>/scripts/scan_jargon.py scan --root <workspace> --diff` | Scans only uncommitted `+` lines and untracked files before committing |
| **Targeted repo / path / language** | `python3 <skill-dir>/scripts/scan_jargon.py scan --root <workspace> --full --repo <name> --path src/` | Repeatable `--repo`, `--path`, and `--lang {all,zh,en}` flags for scoped cleanup |
| **Full workspace audit** | `python3 <skill-dir>/scripts/scan_jargon.py scan --root <workspace> --full --limit 200` | Scans all mutable files across discovered repo(s); split work across parallel subagents by repo or directory when hit counts are large |

## Workflow (Strict Sequence)

### Step 1 — Run the Scanner and Load Vocabulary Rules

1. Run `scan_jargon.py scan` using the mode matching the user's request (default to `--since 14.days` inside Git repos, or `--full` if requested).
2. Read [`references/vocabulary.md`](references/vocabulary.md) to distinguish `[T1]` (must-replace jargon) from `[T2]` (context-dependent terms where layout alignment, mathematical convergence, or named external features are valid).

### Step 2 — Rewrite in Context (Never Blindly Find-and-Replace)

1. **Preserve exact engineering meaning**: Read each matched sentence and state the concrete mechanism, condition, field, or step in plain Chinese (for Chinese text) or plain English (for English text). Never swap one buzzword for another unnatural phrase.
2. **Forbidden / frozen file boundaries** (auto-excluded by the scanner; never edit manually):
   - `CHANGELOG.md`, `VERSION`, `branches.yaml`, `changelog/`, `artifacts/`
   - `contracts/`, `**/archive/**`, `dev-docs/archive/`, `docs/archive/`
   - `*.sql`, `*.pb.go`, `*.lock`, lockfiles, `swagger.json`, `swagger.yaml`, `docs.go`
3. **Never alter identifiers or protocol contracts**: Leave variable/function/type names, JSON keys, API routes, enum values, CLI flags, environment variables, Git branch names, file paths, and skill names untouched.
4. **Check test assertions before editing runtime strings**: For any finding marked `[check test assertions]` in source files (`.go`, `.py`, `.ts`, `.tsx`, `.js`, `.rs`), search test files (`*_test.go`, `*.test.ts*`, `tests/`, `evals.json`) first. Update paired assertions and run the relevant tests, or leave stable wire-protocol error strings unchanged.
5. **Edit source templates rather than generated outputs**: If wording appears inside generated HTML, OpenAPI/Swagger, or codegen outputs, edit the upstream template/source and regenerate rather than hand-editing generated artifacts.

### Step 3 — Verification Before Handback

1. **Boundary & zero-Tier-1 diff check** (always run):
   ```bash
   python3 <skill-dir>/scripts/scan_jargon.py verify --root <workspace>
   ```
2. **Project checks** (run for any repo where runtime strings, docs, or active specs changed):
   - Run targeted unit/snapshot tests if any runtime or UI string literals were edited.
   - Run the repository's doc, content, or spec validator if documentation or active spec files were edited.

### Step 4 — Report Summary

Report the scanned scope, modified file counts, representative before/after rewrites, any intentionally retained technical terms, and Step 3 verification output. Do not commit automatically unless requested.
