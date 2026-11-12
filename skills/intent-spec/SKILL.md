---
name: intent-spec
description: |
  Guide rough feature ideas into structured specs engineered for Intention Group Review (intent-grouped code and diff review). Trigger when the user explicitly asks to write, draft, create, refine, or break down a requirement, spec, PRD, RFC, implementation plan, or issue description, or asks to plan changes by Intention Groups / semantic intent. First produce a complexity-calibrated Alignment Card (L1/L2/L3 covering Why, orthogonal Intention Groups, Impact, and Non-Goals) in chat for quick confirmation, then save as a Markdown spec (e.g., docs/specs/) or implement group-by-group on request. Do NOT trigger on small obvious bug fixes, copy tweaks, pure code Q&A, or when the user explicitly asks to edit code directly without a spec.
---

# Intent Spec — Spec Authoring for Intention Group Review

## Goal

Downstream code review—especially AI diff review—breaks down when unrelated refactors, shared-contract edits, and core behavioral changes get tangled into alphabetical file diffs. Reviewers lose sight of *why* each hunk exists and struggle to catch scope creep or intent drift.

Use this skill **before writing production code** to turn a rough request into a concise, low-friction **Intent Alignment Card**:
1. Structure future changes so every diff hunk maps cleanly into an orthogonal **Intention Group**.
2. Right-size rigor by complexity (`L1` / `L2` / `L3`)—never force heavy boilerplate onto small changes.
3. Keep human effort minimal: **user states rough intent → agent inspects codebase & drafts card → user confirms in 15 seconds → save spec or implement group-by-group**.

Always match the user's language in your questions, alignment cards, and generated spec files.

---

## Workflow

### Step 1: Quietly Inspect Repository Context

When running inside a repository, gather grounded context before drafting—**without modifying any project files**:
- Check local conventions such as `AGENTS.md`, `CLAUDE.md`, and existing spec folders (`docs/specs/`, `specs/`, `rfcs/`).
- Inspect the 2–5 primary files, schemas, shared utilities, and downstream call sites relevant to the request so `Impact` and group boundaries reflect actual code rather than guesswork.

### Step 2: Calibrate Complexity Tier (`L1` / `L2` / `L3`)

Match template weight to the impact scope of the change:

| Tier | Typical Scope | Card Shape & Required Elements |
| :--- | :--- | :--- |
| **`L1` Single-Intent Micro-Change** | 1–2 files, single well-defined behavior tweak, no cross-module side effects | **3–6 lines**: `Why` (one sentence) + single `Intention Group` (action & verifiable invariant). Omit bulky `Impact` / `Non-Goals` unless a hidden compatibility risk exists. |
| **`L2` Standard Feature (Default)** | 3–12 files spanning schema/contracts, core logic, UI, or tests | **15–25 lines**: `Why` + 2–4 orthogonal `Intention Groups` + concrete `Impact` + targeted `Non-Goals`. |
| **`L3` High-Risk / Architectural** | State-machine rewrites, DB migrations, breaking public API changes | **Full Spec Card**: all four core sections plus **rollout/rollback ordering** across groups, legacy data compatibility, and open trade-off decisions. |

See [references/examples.md](references/examples.md) for concrete `L1`, `L2`, and `L3` examples.

### Step 3: Decompose `What` into Orthogonal Intention Groups

Every Intention Group should read like a standalone chapter title in a future PR review guide:

1. **Group by semantic purpose (`Why`), never file-by-file**
   - Avoid: `1. Update order.ts  2. Edit schema.sql  3. Change OrderCard.tsx`
   - Prefer: `1. [Data Contract] Add order expiration field & types  2. [Core Logic] Enforce timeout cancellation  3. [UI Surface] Render countdown state on order cards`
2. **Isolate preparatory refactors from behavior changes**
   - When legacy code needs cleanup before new logic fits cleanly, split out `Group 1: [Preparatory Refactor] ...` with the explicit invariant: `Pure structural extraction; 100% identical runtime behavior and passing existing tests`. Never mix refactoring and new behavior in the same group.
3. **Call out shared modules and public contracts explicitly**
   - Changes to global utilities, shared types, middleware, or schemas belong either in their own group or explicitly named under `Impact` with affected callers listed so reviewers know where to focus scrutiny.
4. **Attach a verifiable Invariant to every group**
   - Replace vague claims ("works properly", "clean code") with checkable guarantees (e.g., `Legacy records missing expire_at default to never-expiring without throwing`).
5. **Lock out scope creep and diff noise via `Non-Goals`**
   - Combine **adjacent product boundaries** (e.g., `Applies only to checkout creation, not post-purchase refund flows`) with **diff hygiene rules** (no drive-by symbol renames, no unrelated formatting churn).

### Step 4: Draft First, Interrogate Less

Editing a concrete draft is much easier for the user than answering an open-ended questionnaire:
- **When a missing decision materially alters the design**: ask at most **1–3 concise multiple-choice questions** with your recommended option listed first.
- **Otherwise**: make reasonable assumptions, present the **Intent Alignment Card** directly in chat, and surface any minor assumptions in a 1–2 line confirmation prompt at the bottom.

---

## Chat Alignment Card Template (`L2` / `L3`)

Keep the initial in-chat card scannable:

```markdown
## Intent Alignment Card: <Concise Title> `[L2 Standard Feature]`

### 1. Why (Motivation & Problem)
- <1–2 sentences stating the user/system problem or root cause, without implementation minutiae>

### 2. Intention Groups (Orthogonal Change Buckets)
1. **[Group 1 — <Role: Verb + Object, e.g., Preparatory Refactor: Extract pure pricing helpers>]**
   - **Scope**: <Target module responsibilities and core change>
   - **Invariant**: <Concrete correctness or compatibility guarantee reviewers can verify>
2. **[Group 2 — <e.g., Data Contract: Extend Order schema with expiration timestamp>]**
   - **Scope**: ...
   - **Invariant**: ...
3. **[Group 3 — <e.g., Core Logic & Tests: Enforce automatic timeout cancellation>]**
   - **Scope**: ...
   - **Invariant**: ...

### 3. Impact (Affected Scope & Review Hotspots)
- **Touched Shared Modules / Contracts**: <Shared types, utilities, APIs, or migrations; or "Isolated within <module>">
- **Compatibility & Legacy Data**: <Backward compatibility, defaults for existing records, or feature flags>

### 4. Non-Goals (Out of Scope & Diff Hygiene)
- <Product boundary: adjacent flows intentionally untouched in this change>
- **Diff Hygiene**: No unrelated renames or formatting edits; keep pure refactors strictly separate from behavior changes.
```

> End with a brief confirmation prompt:
> - Does this intent breakdown and boundary look right?
> - Once confirmed, would you like to **save it as a Markdown spec** (default `docs/specs/YYYY-MM-DD-<slug>.md` or repo convention), **implement group-by-group now**, or **export as an Issue / PR description**?

---

## Step 5: Post-Confirmation Handoff

Once the user approves or refines the card, follow their chosen path:

### Path A: Persist as a Markdown Spec File
1. Follow existing repository spec conventions (`docs/specs/`, `specs/`, `rfcs/`); if none exist, write to `docs/specs/YYYY-MM-DD-<slug>.md`.
2. Append a concise **Execution & Review Contract** section at the bottom for whoever implements and reviews the spec:
   - Implement `Intention Groups` in sequence, verifying each group's `Invariant` before moving on, ideally landing one atomic commit per Intention Group.
   - If implementation uncovers a required change outside `Non-Goals` or touches unannounced shared contracts, surface and split it into a new Intention Group rather than silently bundling it into an existing group.

### Path B: Implement Directly by Intention Group
1. Treat the confirmed `Intention Groups` as your execution plan and work through them **one group at a time**, keeping hunks clean of unrelated edits.
2. When committing is part of the workflow, create clean atomic commits aligned 1-to-1 with each Intention Group; when leaving unstaged changes for local review, organize your final summary **strictly by Intention Group**, citing modified files/lines, verified invariants, and confirming zero unrequested scope drift.
