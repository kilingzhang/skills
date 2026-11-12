# Intent Spec Calibration Examples (`L1` / `L2` / `L3`)

These examples illustrate how to translate rough, conversational feature requests into right-sized **Intent Alignment Cards** optimized for **Intention Group Review**—without forcing rigid bureaucracy onto small tasks.

---

## Example 1: `L1 Single-Intent Micro-Change` (Zero Boilerplate)

**User Input**:
> Help me spec a quick requirement: when a coupon discounts the payable order total down to $0, the checkout settlement endpoint throws a division-by-zero error. We need to handle $0 totals cleanly.

**Alignment Card Output (5 lines)**:
```markdown
## Intent Alignment Card: Guard Zero-Amount Order Settlement Against Division by Zero `[L1 Micro-Change]`

- **Why**: Full-discount coupons produce `payableAmount === 0`, causing proportional discount allocation to divide by zero and block `$0` checkouts.
- **Intention Group**: **[Boundary Guard] Short-circuit zero-total allocation in settlement calculator**
  - **Scope**: Return zeroed allocation shares early in `calculateDiscountAllocation` when total or payable amount is `0`, plus unit test coverage for `$0` orders.
  - **Invariant**: Allocation rounding and precision for `payableAmount > 0` remain 100% unchanged; request/response schemas stay untouched.
```
> Looks right? Let me know if I should implement this directly or save a short spec note.

---

## Example 2: `L2 Standard Feature` (Separating Refactor, Contract, and UI)

**User Input**:
> Let's write a spec: add a "Pin" feature to the task list, max 5 pinned tasks, persisted across page reloads. Also, the current task sorting code is jammed inline inside the component and super messy—let's clean that up too.

**Why Orthogonal Grouping Matters Here**:
If an agent extracts the inline sorting logic *and* adds pinned-priority sorting inside the same diff hunk, a reviewer cannot easily verify whether the default unpinned sort order accidentally changed.

**Alignment Card Output**:
```markdown
## Intent Alignment Card: Persistent Task Pinning (Max 5 Items) `[L2 Standard Feature]`

### 1. Why (Motivation & Problem)
- High-priority tasks get buried under new entries; users need persistent manual pinning (capped at 5 items). Inline sorting inside the list component also needs to be extracted first so pinning rules are not layered onto tangled view code.

### 2. Intention Groups (Orthogonal Change Buckets)
1. **[Group 1 — Preparatory Refactor: Extract pure task-sorting helper]**
   - **Scope**: Move inline sort comparator from `TaskList.tsx` into `utils/sortTasks.ts` with baseline unit tests.
   - **Invariant**: Pure structural extraction; unpinned task ordering matches existing runtime behavior 100%.
2. **[Group 2 — Data Contract & Persistence: Add `pinnedAt` field and 5-item cap]**
   - **Scope**: Add optional `pinnedAt?: number` to `Task` model and persistence store; implement pin/unpin mutations that reject a 6th pin cleanly.
   - **Invariant**: Existing stored tasks without `pinnedAt` deserialize as unpinned; exceeding 5 pinned items returns a typed validation error without mutating state.
3. **[Group 3 — Sorting & UI Controls: Prioritize pinned tasks and add pin toggle]**
   - **Scope**: Update `sortTasks` to rank pinned items first (`pinnedAt` descending) and add pin/unpin action button + limit toast in `TaskRow.tsx`.
   - **Invariant**: Unpinning a task immediately restores it to its original chronological position.

### 3. Impact (Blast Radius & Review Hotspots)
- **Touched Shared Modules / Contracts**: `types/task.ts` (`Task` interface), task storage adapter, and `TaskList` / `TaskRow` components.
- **Compatibility & Legacy Data**: Backward-compatible optional `pinnedAt` field; no destructive storage migration needed.

### 4. Non-Goals (Out of Scope & Diff Hygiene)
- Custom drag-and-drop reordering among pinned items is out of scope (ordered strictly by `pinnedAt` descending).
- Archived and trashed task views are unchanged.
- **Diff Hygiene**: Keep Group 1 (pure refactor) strictly separate from Groups 2–3 (feature behavior); no unrelated styling tweaks or state field renames.
```

---

## Example 3: `L3 Architectural / Breaking-Risk Change` (Rollout & Rollback Boundaries)

When a spec involves **schema deprecations, authentication flow rewrites, or cross-service contract changes**, upgrade to `[L3 Architectural Change]` and explicitly sequence Intention Groups for safe incremental rollout and rollback:

1. **Group 1 — Expand Contract**: Add new schema columns/fields and backward-compatible readers (safe no-op deploy).
2. **Group 2 — Dual-Write & Backfill**: Write to both legacy and new fields; backfill historical records idempotently.
3. **Group 3 — Switch Primary Reads**: Cut read paths over to the new contract behind a toggle or verified invariant.
4. **Group 4 — Contract Cleanup (Deferred / Separate PR)**: Drop deprecated fields only after verification window closes.

Surface any unresolved architectural trade-offs under an explicit **Open Decisions** block at the bottom of the card before persisting the final spec.
