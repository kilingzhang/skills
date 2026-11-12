#!/usr/bin/env python3
"""
Deterministic inventory, real skill-usage telemetry, snapshotting, and post-edit
verification helper for the context-slim skill. Pure Python 3 stdlib.
"""

from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Set, Tuple


FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
AT_IMPORT_RE = re.compile(r"(?m)^@([^\s#]+)\s*$")
CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")

IGNORE_WALK_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".build",
    "target",
    ".venv",
    "venv",
    "__pycache__",
    ".turbo",
}


def approx_tokens(text: str) -> int:
    cjk = len(CJK_RE.findall(text))
    non_cjk = max(0, len(text) - cjk)
    return int(round(cjk * 0.7 + non_cjk / 4.0))


def parse_frontmatter_raw(text: str) -> Tuple[Dict[str, object], str]:
    """Lightweight stdlib YAML frontmatter parser for name, description, when_to_use, paths."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw_fm = m.group(1)
    body = text[m.end() :]
    lines = raw_fm.splitlines()
    data: Dict[str, object] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line or line[0].isspace():
            i += 1
            continue
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if rest in ("|", ">", "|-", ">-"):
            block: List[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or not lines[i].strip()):
                block.append(lines[i].lstrip())
                i += 1
            data[key] = "\n".join(block).strip()
            continue
        if rest == "":
            items: List[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or lines[i].lstrip().startswith("-")):
                item = lines[i].strip()
                if item.startswith("-"):
                    val = item[1:].strip().strip("\"'")
                    if val:
                        items.append(val)
                i += 1
            data[key] = items
            continue
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            data[key] = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()] if inner else []
        else:
            data[key] = rest.strip("\"'")
        i += 1
    return data, body


def list_repo_files(repo: Path) -> List[str]:
    out: List[str] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_WALK_DIRS]
        rel_root = Path(root).relative_to(repo)
        for f in files:
            rel = (rel_root / f).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            out.append(rel)
    return sorted(out)


def expand_brace_globs(pattern: str) -> List[str]:
    m = re.search(r"\{([^{}]+)\}", pattern)
    if not m:
        return [pattern]
    prefix, suffix = pattern[: m.start()], pattern[m.end() :]
    results: List[str] = []
    for opt in m.group(1).split(","):
        results.extend(expand_brace_globs(prefix + opt.strip() + suffix))
    return results


def glob_matches_path(pattern: str, rel_path: str) -> bool:
    for pat in expand_brace_globs(pattern.strip()):
        pat = pat.lstrip("./")
        regex_parts: List[str] = ["^"]
        i = 0
        while i < len(pat):
            if pat[i : i + 3] == "**/":
                regex_parts.append("(?:.+/)?")
                i += 3
            elif pat[i : i + 2] == "**":
                regex_parts.append(".*")
                i += 2
            elif pat[i] == "*":
                regex_parts.append("[^/]*")
                i += 1
            elif pat[i] == "?":
                regex_parts.append("[^/]")
                i += 1
            else:
                regex_parts.append(re.escape(pat[i]))
                i += 1
        regex_parts.append("$")
        if re.match("".join(regex_parts), rel_path):
            return True
        if "/" not in pat and fnmatch.fnmatch(PurePosixPath(rel_path).name, pat):
            return True
    return False


def match_paths_globs(patterns: Iterable[str], repo_files: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for pat in patterns:
        counts[pat] = sum(1 for f in repo_files if glob_matches_path(pat, f))
    return counts


def resolve_at_imports(file_path: Path) -> List[Tuple[str, Optional[Path]]]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    found: List[Tuple[str, Optional[Path]]] = []
    for m in AT_IMPORT_RE.finditer(text):
        raw = m.group(1).strip()
        candidate = Path(os.path.expanduser(raw))
        if not candidate.is_absolute():
            candidate = (file_path.parent / candidate).resolve()
        found.append((raw, candidate if candidate.is_file() else None))
    return found


def discover_skills(repo: Path, include_global: bool = True) -> Dict[str, Dict[str, object]]:
    """Return map of skill_name -> metadata across project and global skill dirs."""
    locations: List[Tuple[str, Path]] = [
        ("project:.agents", repo / ".agents" / "skills"),
        ("project:.claude", repo / ".claude" / "skills"),
        ("project:.codex", repo / ".codex" / "skills"),
        ("project:skills", repo / "skills"),
    ]
    if include_global:
        home = Path.home()
        locations.extend(
            [
                ("global:.agents", home / ".agents" / "skills"),
                ("global:.claude", home / ".claude" / "skills"),
                ("global:.codex", home / ".codex" / "skills"),
                ("global:.gemini", home / ".gemini" / "skills"),
            ]
        )

    skills: Dict[str, Dict[str, object]] = {}
    for label, root in locations:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.name.startswith("."):
                continue
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                continue
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm, body = parse_frontmatter_raw(text)
            name = str(fm.get("name") or entry.name).strip()
            desc = str(fm.get("description") or "")
            wtu = str(fm.get("when_to_use") or "")
            refs_chars = 0
            refs_dir = entry / "references"
            if refs_dir.is_dir():
                for rf in refs_dir.rglob("*"):
                    if rf.is_file():
                        try:
                            refs_chars += len(rf.read_text(encoding="utf-8", errors="replace"))
                        except OSError:
                            pass
            rec = skills.setdefault(
                name,
                {
                    "name": name,
                    "path": str(skill_md.resolve()),
                    "harnesses": [],
                    "desc_chars": len(desc) + len(wtu),
                    "has_when_to_use": bool(wtu),
                    "body_chars": len(body),
                    "refs_chars": refs_chars,
                },
            )
            if label not in rec["harnesses"]:  # type: ignore[operator]
                rec["harnesses"].append(label)  # type: ignore[union-attr]
    return skills


def cmd_inventory(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    repo_files = list_repo_files(repo) if repo.is_dir() else []
    home = Path.home()

    always_rows: List[Tuple[str, int, int, str]] = []
    ondemand_rows: List[Tuple[str, int, int, str]] = []
    warnings: List[str] = []

    if (repo / "CLAUDE.md").is_file() and (repo / "AGENTS.md").is_file():
        warnings.append(
            "Root `CLAUDE.md` and `AGENTS.md` both exist: Claude Code will read `CLAUDE.md` and skip root `AGENTS.md`."
        )
    elif (repo / "CLAUDE.md").is_file() and not (repo / "AGENTS.md").is_file():
        warnings.append(
            "Root `CLAUDE.md` exists without `AGENTS.md`: non-Claude harnesses (Codex, etc.) will not read root `CLAUDE.md`."
        )

    def add_doc(label: str, path: Path, tier: str, note: str = "") -> None:
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        row = (label, len(text), approx_tokens(text), note)
        if tier == "always":
            always_rows.append(row)
        else:
            ondemand_rows.append(row)
        for raw_imp, resolved in resolve_at_imports(path):
            if resolved is None:
                warnings.append(f"`{label}` contains unresolved `@` import: `@{raw_imp}`")
            else:
                imp_txt = resolved.read_text(encoding="utf-8", errors="replace")
                imp_row = (f"  ↳ @{raw_imp}", len(imp_txt), approx_tokens(imp_txt), f"transcluded by {label}")
                if tier == "always":
                    always_rows.append(imp_row)
                else:
                    ondemand_rows.append(imp_row)

    for root_name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules"):
        add_doc(f"repo:{root_name}", repo / root_name, "always", "root instruction")

    rules_dir = repo / ".claude" / "rules"
    if rules_dir.is_dir():
        for rf in sorted(rules_dir.rglob("*.md")):
            rel = rf.relative_to(repo).as_posix()
            txt = rf.read_text(encoding="utf-8", errors="replace")
            fm, _ = parse_frontmatter_raw(txt)
            paths_val = fm.get("paths")
            if isinstance(paths_val, str):
                paths_list = [paths_val]
            elif isinstance(paths_val, list):
                paths_list = [str(x) for x in paths_val]
            else:
                paths_list = []
            if not paths_list:
                always_rows.append((f"repo:{rel}", len(txt), approx_tokens(txt), "unscoped .claude/rules (no paths:)"))
            else:
                counts = match_paths_globs(paths_list, repo_files)
                zero = [p for p, c in counts.items() if c == 0]
                if zero:
                    warnings.append(f"`{rel}` has `paths:` glob(s) matching 0 files: {zero}")
                summary = ", ".join(f"{p} ({c})" for p, c in counts.items())
                ondemand_rows.append((f"repo:{rel}", len(txt), approx_tokens(txt), f"paths: {summary}"))

    for rel in repo_files:
        if rel in ("AGENTS.md", "CLAUDE.md", "GEMINI.md") or rel.startswith(".claude/rules/"):
            continue
        base = PurePosixPath(rel).name
        if base in ("AGENTS.md", "CLAUDE.md"):
            add_doc(f"repo:{rel}", repo / rel, "ondemand", "subdirectory instruction")
        elif rel.startswith("docs/") and rel.endswith(".md"):
            add_doc(f"repo:{rel}", repo / rel, "ondemand", "docs markdown")

    if not args.no_global:
        add_doc("global:~/.claude/CLAUDE.md", home / ".claude" / "CLAUDE.md", "always", "Claude global")
        add_doc("global:~/.codex/AGENTS.md", home / ".codex" / "AGENTS.md", "always", "Codex global")
        add_doc("global:~/.gemini/GEMINI.md", home / ".gemini" / "GEMINI.md", "always", "Gemini global")
        g_rules = home / ".claude" / "rules"
        if g_rules.is_dir():
            for rf in sorted(g_rules.rglob("*.md")):
                txt = rf.read_text(encoding="utf-8", errors="replace")
                fm, _ = parse_frontmatter_raw(txt)
                has_paths = bool(fm.get("paths"))
                tier = "ondemand" if has_paths else "always"
                add_doc(f"global:~/.claude/rules/{rf.name}", rf, tier, "scoped" if has_paths else "unscoped global rule")

    skills = discover_skills(repo, include_global=not args.no_global)
    proj_skill_desc = 0
    glob_skill_desc = 0
    for s in skills.values():
        harnesses: List[str] = s["harnesses"]  # type: ignore[assignment]
        is_proj = any(h.startswith("project:") for h in harnesses)
        if is_proj:
            proj_skill_desc += int(s["desc_chars"])  # type: ignore[arg-type]
        else:
            glob_skill_desc += int(s["desc_chars"])  # type: ignore[arg-type]
        ondemand_rows.append(
            (
                f"skill:{s['name']} (body+refs)",
                int(s["body_chars"]) + int(s["refs_chars"]),  # type: ignore[arg-type]
                approx_tokens("x" * (int(s["body_chars"]) + int(s["refs_chars"]))),  # type: ignore[arg-type]
                f"desc={s['desc_chars']} chars | {','.join(harnesses)}",
            )
        )

    if proj_skill_desc:
        always_rows.append(("skills:project descriptions", proj_skill_desc, proj_skill_desc // 4, "loaded every turn"))
    if glob_skill_desc:
        always_rows.append(
            (
                f"skills:global descriptions ({len(skills)} skills)",
                glob_skill_desc,
                glob_skill_desc // 4,
                "loaded every turn",
            )
        )

    total_always_chars = sum(r[1] for r in always_rows)
    total_always_tok = sum(r[2] for r in always_rows)

    print("## 1. Every-Turn (Always-Loaded) Context Inventory\n")
    print("| Source | Chars | ~Tokens | Share | Notes |")
    print("| :--- | ---: | ---: | ---: | :--- |")
    for label, chars, tok, note in always_rows:
        pct = (chars / total_always_chars * 100.0) if total_always_chars else 0.0
        print(f"| `{label}` | {chars:,} | {tok:,} | {pct:4.1f}% | {note} |")
    print(f"| **TOTAL ALWAYS-LOADED** | **{total_always_chars:,}** | **{total_always_tok:,}** | **100%** | |")

    print("\n## 2. On-Demand Context Inventory\n")
    print("| Source | Chars | ~Tokens | Notes |")
    print("| :--- | ---: | ---: | :--- |")
    for label, chars, tok, note in sorted(ondemand_rows, key=lambda x: x[1], reverse=True)[:40]:
        print(f"| `{label}` | {chars:,} | {tok:,} | {note} |")
    if len(ondemand_rows) > 40:
        print(f"| *(+{len(ondemand_rows) - 40} smaller on-demand items omitted)* | | | |")

    if warnings:
        print("\n## 3. Structural Warnings\n")
        for w in warnings:
            print(f"- WARNING: {w}")
    return 0


def cmd_skill_usage(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    skills = discover_skills(repo, include_global=not args.no_global)
    names = sorted(skills.keys(), key=len, reverse=True)
    if not names:
        print("No installed skills found.")
        return 0

    counts: Dict[str, int] = {n: 0 for n in names}
    last_ts: Dict[str, str] = {n: "-" for n in names}
    escaped = "|".join(re.escape(n) for n in names)
    path_re = re.compile(rf"skills/({escaped})(?:/|\"|\'|\s|$)")
    slash_re = re.compile(rf"(?:^|[\s\"'>])[\$/]({escaped})(?:$|[\s\"'<.,:;])")

    def record(name: str, ts: str) -> None:
        if name in counts:
            counts[name] += 1
            if ts and (last_ts[name] == "-" or ts > last_ts[name]):
                last_ts[name] = ts[:10]

    home = Path.home()
    claude_logs = glob.glob(str(home / ".claude" / "projects" / "**" / "*.jsonl"), recursive=True)
    for lf in claude_logs:
        try:
            with open(lf, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "skill_listing" in line or "api-request-shape" in line:
                        continue
                    if "SKILL.md" not in line and '"Skill"' not in line and "skills/" not in line and "/" not in line and "$" not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg_type = obj.get("type")
                    ts = str(obj.get("timestamp") or "")
                    if msg_type == "assistant":
                        content = obj.get("message", {}).get("content", [])
                        if isinstance(content, list):
                            for blk in content:
                                if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                                    continue
                                if blk.get("name") == "Skill":
                                    sk = str((blk.get("input") or {}).get("skill") or "").strip("/")
                                    record(sk, ts)
                                else:
                                    raw_in = json.dumps(blk.get("input") or {})
                                    for m in path_re.finditer(raw_in):
                                        record(m.group(1), ts)
                    elif msg_type == "user":
                        raw_msg = json.dumps(obj.get("message") or {})
                        for m in slash_re.finditer(raw_msg):
                            record(m.group(1), ts)
        except OSError:
            continue

    codex_logs = glob.glob(str(home / ".codex" / "sessions" / "**" / "*.jsonl"), recursive=True) + glob.glob(
        str(home / ".codex" / "archived_sessions" / "**" / "*.jsonl"), recursive=True
    )
    for lf in codex_logs:
        try:
            with open(lf, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "session_meta" in line or "turn_context" in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = str(obj.get("timestamp") or "")
                    payload = obj.get("payload")
                    if not isinstance(payload, dict):
                        continue
                    ptype = payload.get("type")
                    role = payload.get("role")
                    if role == "developer":
                        continue
                    if ptype in ("function_call", "custom_tool_call"):
                        args_str = str(payload.get("arguments") or payload.get("input") or "")
                        for m in path_re.finditer(args_str):
                            record(m.group(1), ts)
                    elif ptype == "message" and role == "user":
                        txt = json.dumps(payload.get("content") or "")
                        for m in slash_re.finditer(txt):
                            record(m.group(1), ts)
        except OSError:
            continue

    t3_logs = glob.glob(str(home / ".t3" / "userdata" / "**" / "transcript.jsonl"), recursive=True)
    for lf in t3_logs:
        try:
            with open(lf, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = str(obj.get("created_at") or "")
                    stype = obj.get("type")
                    if stype == "PLANNER_RESPONSE":
                        tcs = json.dumps(obj.get("tool_calls") or [])
                        for m in path_re.finditer(tcs):
                            record(m.group(1), ts)
                    elif stype == "USER_INPUT":
                        txt = str(obj.get("content") or "")
                        for m in slash_re.finditer(txt):
                            record(m.group(1), ts)
        except OSError:
            continue

    print("## Installed Skill Telemetry (Real Transcript Invocations)\n")
    print(
        f"Scanned {len(claude_logs)} Claude, {len(codex_logs)} Codex, and {len(t3_logs)} T3 session transcripts.\n"
    )
    print("| Skill | Invocations | Last Used | Desc Chars | Harnesses |")
    print("| :--- | ---: | :--- | ---: | :--- |")
    for name, rec in sorted(skills.items(), key=lambda kv: (counts[kv[0]], -int(kv[1]["desc_chars"]))):  # type: ignore[arg-type]
        harnesses = ",".join(rec["harnesses"])  # type: ignore[arg-type]
        print(f"| `{name}` | {counts[name]} | {last_ts[name]} | {rec['desc_chars']} | {harnesses} |")
    return 0


def collect_context_files(repo: Path) -> List[Path]:
    files: List[Path] = []
    for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules"):
        p = repo / name
        if p.is_file():
            files.append(p)
    for sub in (".claude/rules", "docs", "skills", ".agents/skills", ".claude/skills"):
        d = repo / sub
        if d.is_dir():
            files.extend(sorted(p for p in d.rglob("*.md") if p.is_file()))
    for rf in list_repo_files(repo):
        if rf not in ("AGENTS.md", "CLAUDE.md") and PurePosixPath(rf).name in ("AGENTS.md", "CLAUDE.md"):
            files.append(repo / rf)
    seen: Set[Path] = set()
    uniq: List[Path] = []
    for p in files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def cmd_snapshot(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    manifest: List[Dict[str, str]] = []
    targets = collect_context_files(repo)
    for extra in args.extra:
        ep = Path(os.path.expanduser(extra)).resolve()
        if ep.is_file():
            targets.append(ep)

    for idx, src in enumerate(targets):
        dest_name = f"{idx:03d}__{src.name}"
        shutil.copy2(src, out / dest_name)
        manifest.append({"src": str(src), "backup": dest_name})

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Snapshotted {len(manifest)} context file(s) to {out}")
    return 0


def normalize_meaningful_lines(text: str) -> List[str]:
    out: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s in ("---", "```"):
            continue
        out.append(s)
    return out


def cmd_verify(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    repo_files = list_repo_files(repo)
    errors = 0

    print("## 1. `paths:` Glob Verification\n")
    rules_dir = repo / ".claude" / "rules"
    if rules_dir.is_dir():
        for rf in sorted(rules_dir.rglob("*.md")):
            rel = rf.relative_to(repo).as_posix()
            fm, _ = parse_frontmatter_raw(rf.read_text(encoding="utf-8", errors="replace"))
            pv = fm.get("paths")
            plist = [pv] if isinstance(pv, str) else ([str(x) for x in pv] if isinstance(pv, list) else [])
            if not plist:
                print(f"- `{rel}`: unscoped (loads every turn)")
                continue
            counts = match_paths_globs(plist, repo_files)
            for pat, c in counts.items():
                status = "OK" if c > 0 else "FAIL (0 matches)"
                if c == 0:
                    errors += 1
                print(f"- `{rel}` glob `{pat}` -> {c} file(s) [{status}]")
    else:
        print("- No `.claude/rules/` directory present.")

    if args.removed_names:
        print("\n## 2. Stale Filename Reference Check\n")
        names = [n.strip() for n in args.removed_names.split(",") if n.strip()]
        for name in names:
            hits: List[str] = []
            for rel in repo_files:
                if not rel.endswith((".md", ".json", ".yaml", ".yml", ".toml", ".sh")):
                    continue
                txt = (repo / rel).read_text(encoding="utf-8", errors="ignore")
                if name in txt:
                    hits.append(rel)
            if hits:
                errors += 1
                print(f"- FAIL: Removed name `{name}` still referenced in: {hits}")
            else:
                print(f"- OK: `{name}` has 0 stale references.")

    if args.snapshot:
        snap_dir = Path(args.snapshot).resolve()
        manifest = json.loads((snap_dir / "manifest.json").read_text(encoding="utf-8"))
        before_lines: List[Tuple[str, str]] = []
        for item in manifest:
            btxt = (snap_dir / item["backup"]).read_text(encoding="utf-8", errors="replace")
            for ln in normalize_meaningful_lines(btxt):
                before_lines.append((item["src"], ln))

        current_files = collect_context_files(repo)
        for item in manifest:
            sp = Path(item["src"])
            if sp.is_file() and sp not in current_files:
                current_files.append(sp)

        after_pool: Set[str] = set()
        per_file_after: Dict[str, Set[str]] = {}
        for cf in current_files:
            if cf.is_file():
                lns = set(normalize_meaningful_lines(cf.read_text(encoding="utf-8", errors="replace")))
                per_file_after[str(cf)] = lns
                after_pool.update(lns)

        relocated = 0
        disappeared: List[Tuple[str, str]] = []
        seen_disappeared: Set[str] = set()
        for src, ln in before_lines:
            still_in_same = ln in per_file_after.get(src, set())
            if still_in_same:
                continue
            if ln in after_pool:
                relocated += 1
            elif ln not in seen_disappeared:
                seen_disappeared.add(ln)
                disappeared.append((src, ln))

        out_file = snap_dir / "disappeared_lines.txt"
        out_file.write_text(
            "\n".join(f"[{Path(src).name}] {ln}" for src, ln in disappeared) + ("\n" if disappeared else ""),
            encoding="utf-8",
        )
        print("\n## 3. Snapshot Line Reconciliation\n")
        print(f"- Lines relocated verbatim to new on-demand files: **{relocated}**")
        print(f"- Unique lines absent from post-edit context (`disappeared_lines.txt`): **{len(disappeared)}**")
        print(f"- Saved disappeared lines for Step 11 & Step 12 blind subagent audit: `{out_file}`")

    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and verify agent context & installed skills.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inv = sub.add_parser("inventory", help="Measure always-loaded vs. on-demand context.")
    p_inv.add_argument("--repo", default=".", help="Repository root path")
    p_inv.add_argument("--no-global", action="store_true", help="Skip global ~/.claude, ~/.codex, ~/.gemini")
    p_inv.set_defaults(func=cmd_inventory)

    p_use = sub.add_parser("skill-usage", help="Audit real skill invocations from transcripts.")
    p_use.add_argument("--repo", default=".", help="Repository root path")
    p_use.add_argument("--no-global", action="store_true", help="Skip global skills")
    p_use.set_defaults(func=cmd_skill_usage)

    p_snap = sub.add_parser("snapshot", help="Snapshot context files prior to editing.")
    p_snap.add_argument("--repo", default=".", help="Repository root path")
    p_snap.add_argument("--out", required=True, help="Output snapshot directory")
    p_snap.add_argument("extra", nargs="*", help="Optional extra files (e.g. ~/.claude/CLAUDE.md)")
    p_snap.set_defaults(func=cmd_snapshot)

    p_ver = sub.add_parser("verify", help="Verify paths: globs, stale refs, and disappeared lines.")
    p_ver.add_argument("--repo", default=".", help="Repository root path")
    p_ver.add_argument("--snapshot", help="Snapshot directory created before edits")
    p_ver.add_argument("--removed-names", help="Comma-separated old filenames to grep for stale refs")
    p_ver.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
