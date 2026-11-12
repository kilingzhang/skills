#!/usr/bin/env python3
"""Deterministic bilingual (ZH + EN) jargon scanner & boundary verifier for plain-language.

Works across any single Git repository, multi-repo workspace, or plain directory.

Subcommands:
  scan [--root DIR] [--since 14.days | --diff | --full] [--whole-file]
       [--repo REPO ...] [--path SUBSTR ...] [--tier {1,all}] [--lang {all,zh,en}]
       [--limit N] [--json]
  verify [--root DIR] [--repo REPO ...] [--path SUBSTR ...] [--lang {all,zh,en}]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SKIP_DISCOVERY_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "dist",
    "build",
    ".build",
    "target",
    "__pycache__",
    ".next",
    ".turbo",
}

FORBIDDEN_EXACT = {
    "branches.yaml",
    "CHANGELOG.md",
    "VERSION",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "bun.lockb",
    "bun.lock",
    "go.sum",
    "Cargo.lock",
    "poetry.lock",
    "uv.lock",
    "docs/docs.go",
    "docs/swagger.json",
    "docs/swagger.yaml",
}

FORBIDDEN_PREFIXES = (
    "changelog/",
    "artifacts/",
    "contracts/",
    "dev-docs/archive/",
    "docs/archive/",
)

FORBIDDEN_SUBSTRINGS = (
    "/archive/",
    "/openspec/changes/archive/",
    "/.coordination/",
    "/skills/plain-language/",
    "/.claude/skills/plain-language/",
    "/.agents/skills/plain-language/",
    "/.codex/skills/plain-language/",
)

FORBIDDEN_SUFFIXES = (
    ".sql",
    ".pb.go",
    ".lock",
    ".min.js",
    ".min.css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".pyc",
    ".so",
    ".dylib",
    ".exe",
)

GENERATED_BASENAME_HINTS = {
    "swagger.json": "Generated OpenAPI/Swagger artifact; update upstream annotations and regenerate instead of hand-editing.",
    "swagger.yaml": "Generated OpenAPI/Swagger artifact; update upstream annotations and regenerate instead of hand-editing.",
    "docs.go": "Generated Swagger Go bindings; update upstream annotations and regenerate instead of hand-editing.",
}


@dataclass(frozen=True)
class TermRule:
    term: str
    lang: str  # "zh" or "en"
    tier: int  # 1 = high-certainty jargon, 2 = context-dependent jargon
    suggestion: str
    pattern_re: re.Pattern[str] | None = None
    whitelist_re: re.Pattern[str] | None = None


def _en_pat(expr: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9_/-])(?<![A-Za-z0-9_]\.)(?:{expr})(?![A-Za-z0-9_/-])(?!\.[A-Za-z0-9_])",
        re.IGNORECASE,
    )


# Chinese vocabulary (23 Tier-1 + 10 Tier-2 = 33 rules)
ZH_RULES: list[TermRule] = [
    TermRule("门禁", "zh", 1, "检查 / 校验 / 拦截条件 / 确认步骤 / 准入条件", whitelist_re=re.compile(r"门禁卡|刷门禁|大厦门禁")),
    TermRule("收口", "zh", 1, "结束 / 完成 / 汇总 / 统一归入某处"),
    TermRule("收束", "zh", 1, "结束 / 汇总 / 限制在…范围内"),
    TermRule("兜底", "zh", 1, "默认处理 / 备用方案 / 回退机制 / 保底逻辑"),
    TermRule("兜住", "zh", 1, "拦住 / 捕获 / 覆盖 / 保证不出错"),
    TermRule("口径", "zh", 1, "规则 / 计算方式 / 判断标准 / 时区 / 格式要求", whitelist_re=re.compile(r"小口径|大口径|火炮口径")),
    TermRule("权威源", "zh", 1, "唯一维护位置 / 唯一数据源 / 正式定义处"),
    TermRule("班车", "zh", 1, "定时发布 / 固定周期任务 / 批次", whitelist_re=re.compile(r"通勤班车|下班班车|乘坐班车")),
    TermRule("心智", "zh", 1, "用户理解 / 使用习惯 / 理解成本"),
    TermRule("体感", "zh", 1, "实际体验 / 直观感受 / 响应速度", whitelist_re=re.compile(r"体感温度|体感游戏")),
    TermRule("抓手", "zh", 1, "切入点 / 工具 / 具体手段 / 控制点"),
    TermRule("赋能", "zh", 1, "支持 / 提供…能力 / 让…能够"),
    TermRule("组合拳", "zh", 1, "多项配合措施 / 组合方案"),
    TermRule("颗粒度", "zh", 1, "细化程度 / 粒度 / 拆分细度"),
    TermRule("卡点", "zh", 1, "阻塞问题 / 拦截检查点 / 瓶颈"),
    TermRule("反哺", "zh", 1, "回传 / 补充更新 / 反馈给"),
    TermRule("击穿", "zh", 1, "穿透 / 绕过限制", whitelist_re=re.compile(r"缓存击穿")),
    TermRule("背书", "zh", 1, "担保 / 验证确认 / 签名证明"),
    TermRule("痛点", "zh", 1, "常见问题 / 实际困难 / 不便之处"),
    TermRule("打法", "zh", 1, "做法 / 处理策略 / 实施方案"),
    TermRule("可感知", "zh", 1, "用户可见 / 能看到的 / 明显感知的"),
    TermRule("透出", "zh", 1, "展示 / 显示 / 返回给前端 / 暴露"),
    TermRule("拉齐", "zh", 1, "统一 / 核对一致 / 同步更新"),
    TermRule(
        "收敛",
        "zh",
        2,
        "更新一致 / 全部就绪 / 归并 / 缩减范围 / 处理完毕",
        whitelist_re=re.compile(r"级数收敛|算法收敛|损失收敛|梯度收敛"),
    ),
    TermRule(
        "权威",
        "zh",
        2,
        "以…为准 / 正式定义 / 决定…的字段",
        whitelist_re=re.compile(r"证书颁发权威|权威机构"),
    ),
    TermRule(
        "对齐",
        "zh",
        2,
        "保持一致 / 核对一致 / 匹配",
        whitelist_re=re.compile(
            r"[左右居中顶底上下]对齐|两端对齐|基线对齐|像素对齐|字节对齐|内存对齐|列对齐|文本对齐|图标对齐|网格对齐"
        ),
    ),
    TermRule(
        "沉淀",
        "zh",
        2,
        "保存 / 整理记录 / 归入 / 积累",
        whitelist_re=re.compile(r"化学沉淀|沉淀物"),
    ),
    TermRule(
        "闭环",
        "zh",
        2,
        "完整流程 / 全部走通 / 完成验证 / 有始有终",
        whitelist_re=re.compile(r"闭环控制|PID\s*闭环"),
    ),
    TermRule(
        "水位",
        "zh",
        2,
        "占用率 / 阈值 / 负载水平 / 基线标准",
        whitelist_re=re.compile(r"江河水位|水库水位"),
    ),
    TermRule(
        "底座",
        "zh",
        2,
        "基础服务 / 底层设施 / 公共组件",
        whitelist_re=re.compile(r"充电底座|支架底座|物理底座"),
    ),
    TermRule(
        "账本",
        "zh",
        2,
        "记录表 / 状态记录 / 历史台账",
        whitelist_re=re.compile(r"会计账本|财务账本|分布式账本"),
    ),
    TermRule("护栏", "zh", 2, "安全限制 / 校验规则 / 保护措施", whitelist_re=re.compile(r"公路护栏|阳台护栏")),
    TermRule("下沉", "zh", 2, "移到底层 / 抽到公共层 / 放到下层服务"),
    TermRule("打通", "zh", 2, "接通 / 连通 / 串联起来"),
]

# English corporate buzzwords & AI-cliche vocabulary
EN_RULES: list[TermRule] = [
    TermRule(
        "single source of truth",
        "en",
        1,
        "primary record / canonical file / maintained in ...",
        pattern_re=_en_pat(r"single source of truth|SSOT"),
    ),
    TermRule(
        "source of truth",
        "en",
        1,
        "primary record / canonical file / determined by ...",
        pattern_re=_en_pat(r"(?<!single )source of truth|authoritative source"),
    ),
    TermRule(
        "close the loop",
        "en",
        1,
        "complete the workflow / finish verification / report back",
        pattern_re=_en_pat(r"clos(?:e|es|ed|ing) the loop"),
    ),
    TermRule(
        "mental model",
        "en",
        1,
        "how users understand ... / expected behavior / concept",
        pattern_re=_en_pat(r"mental models?"),
    ),
    TermRule(
        "pain point",
        "en",
        1,
        "problem / limitation / common failure",
        pattern_re=_en_pat(r"pain[- ]points?"),
    ),
    TermRule(
        "empower",
        "en",
        1,
        "let / allow / enable",
        pattern_re=_en_pat(r"empowers?|empowered|empowering|empowerment"),
    ),
    TermRule(
        "synergy",
        "en",
        1,
        "combined effect / working together",
        pattern_re=_en_pat(r"synerg(?:y|ies|istic|ize)"),
    ),
    TermRule(
        "paradigm shift",
        "en",
        1,
        "major change / redesign",
        pattern_re=_en_pat(r"paradigm shifts?"),
    ),
    TermRule(
        "north star",
        "en",
        1,
        "primary goal / target design",
        pattern_re=_en_pat(r"north[- ]star"),
    ),
    TermRule(
        "low-hanging fruit",
        "en",
        1,
        "quick fix / straightforward change",
        pattern_re=_en_pat(r"low[- ]hanging fruits?"),
    ),
    TermRule(
        "move the needle",
        "en",
        1,
        "make a measurable difference / improve ...",
        pattern_re=_en_pat(r"mov(?:e|es|ed|ing) the needle"),
    ),
    TermRule(
        "actionable insight",
        "en",
        1,
        "concrete finding / specific next step",
        pattern_re=_en_pat(r"actionable insights?"),
    ),
    TermRule(
        "puffery (best-in-class / game-changer)",
        "en",
        1,
        "delete hype or state concrete measurable behavior",
        pattern_re=_en_pat(r"best[- ]in[- ]class|world[- ]class|game[- ]chang(?:er|ing)|cutting[- ]edge"),
    ),
    TermRule(
        "AI cliche (delve / tapestry / testament)",
        "en",
        1,
        "inspect / examine / shows",
        pattern_re=_en_pat(r"delv(?:e|es|ed|ing)|tapestr(?:y|ies)|a testament to"),
    ),
    TermRule(
        "corporate idiom (circle back / boil the ocean / double-click on)",
        "en",
        1,
        "revisit / do everything at once / inspect closely",
        pattern_re=_en_pat(r"circle back|boil(?:ing)? the ocean|double[- ]click(?:ing)? on"),
    ),
    TermRule(
        "gatekeep",
        "en",
        1,
        "restrict access / require approval / validate",
        pattern_re=_en_pat(r"gatekeep(?:er|ers|ing)?"),
    ),
    TermRule(
        "guardrail",
        "en",
        2,
        "safety check / validation rule / explicit constraint",
        pattern_re=_en_pat(r"guardrails?"),
    ),
    TermRule(
        "leverage",
        "en",
        2,
        "use / rely on",
        pattern_re=_en_pat(r"leverag(?:e|es|ed|ing)"),
        whitelist_re=re.compile(r"financial leverage|debt leverage", re.IGNORECASE),
    ),
    TermRule(
        "holistic",
        "en",
        2,
        "complete / end-to-end / overall",
        pattern_re=_en_pat(r"holistic(?:ally)?"),
    ),
    TermRule(
        "seamless",
        "en",
        2,
        "automatic / direct / without manual steps",
        pattern_re=_en_pat(r"seamless(?:ly)?"),
    ),
    TermRule(
        "blast radius",
        "en",
        2,
        "impact scope / affected components",
        pattern_re=_en_pat(r"blast radius"),
    ),
    TermRule(
        "escape hatch",
        "en",
        2,
        "override option / manual bypass",
        pattern_re=_en_pat(r"escape hatch(?:es)?"),
    ),
    TermRule(
        "first-class citizen",
        "en",
        2,
        "built-in concept / directly supported",
        pattern_re=_en_pat(r"first[- ]class citizens?"),
    ),
    TermRule(
        "slang metaphor (footgun / silver bullet / band-aid)",
        "en",
        2,
        "error-prone option / universal fix / temporary workaround",
        pattern_re=_en_pat(r"footguns?|silver bullets?|band[- ]aids?"),
    ),
    TermRule(
        "tribal knowledge",
        "en",
        2,
        "undocumented knowledge",
        pattern_re=_en_pat(r"tribal knowledge"),
    ),
]

RULES: list[TermRule] = ZH_RULES + EN_RULES

CODE_EXTS = {".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".rs", ".swift", ".java", ".sh"}
MD_LINK_TARGET_RE = re.compile(r"\]\([^)]+\)")
URL_RE = re.compile(r"https?://\S+")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
QUOTED_STR_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def resolve_workspace(root_arg: str) -> tuple[Path, dict[str, Path], set[str]]:
    """Discover root Git repo (if any) and nested sub-repositories up to depth 2."""
    start = Path(root_arg).resolve()
    top = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if top.returncode == 0 and top.stdout.strip():
        base = Path(top.stdout.strip()).resolve()
    else:
        base = start

    repos: dict[str, Path] = {}
    subrepo_rels: set[str] = set()
    if is_git_repo(base):
        repos["."] = base

    for depth1 in sorted(base.iterdir()) if base.is_dir() else []:
        if not depth1.is_dir() or depth1.name in SKIP_DISCOVERY_DIRS or depth1.name.startswith("."):
            continue
        if is_git_repo(depth1):
            rel = depth1.relative_to(base).as_posix()
            repos[rel] = depth1
            subrepo_rels.add(rel)
            continue
        for depth2 in sorted(depth1.iterdir()):
            if not depth2.is_dir() or depth2.name in SKIP_DISCOVERY_DIRS or depth2.name.startswith("."):
                continue
            if is_git_repo(depth2):
                rel = depth2.relative_to(base).as_posix()
                repos[rel] = depth2
                subrepo_rels.add(rel)

    return base, repos, subrepo_rels


def is_excluded_relpath(repo: str, rel: str, subrepo_rels: set[str]) -> bool:
    rel_norm = rel.strip().replace("\\", "/")
    if not rel_norm:
        return True
    if repo == "." and (rel_norm in subrepo_rels or any(rel_norm.startswith(s + "/") for s in subrepo_rels)):
        return True
    base_name = Path(rel_norm).name
    if rel_norm in FORBIDDEN_EXACT or base_name in FORBIDDEN_EXACT:
        return True
    if any(rel_norm.startswith(p) for p in FORBIDDEN_PREFIXES):
        return True
    padded = "/" + rel_norm
    if any(sub in padded for sub in FORBIDDEN_SUBSTRINGS):
        return True
    if any(rel_norm.lower().endswith(suf) for suf in FORBIDDEN_SUFFIXES):
        return True
    return False


def classify_file(rel: str, line: str) -> str:
    ext = Path(rel).suffix.lower()
    stripped = line.lstrip()
    if ext in {".md", ".mdx", ".txt"}:
        return "doc"
    if ext in CODE_EXTS:
        if stripped.startswith(("//", "#", "/*", "*", "<!--")):
            return "comment"
        return "code_or_ui"
    return "config_or_other"


def extract_english_prose_target(rel: str, base_cleaned: str) -> str:
    """Avoid matching code identifiers in source files or inline code spans in Markdown."""
    ext = Path(rel).suffix.lower()
    if ext in {".md", ".mdx", ".txt"}:
        return INLINE_CODE_RE.sub(" ", base_cleaned)
    if ext in CODE_EXTS:
        stripped = base_cleaned.lstrip()
        if stripped.startswith(("//", "#", "/*", "*", "<!--")):
            return INLINE_CODE_RE.sub(" ", stripped)
        literals = QUOTED_STR_RE.findall(base_cleaned)
        return " ".join(literals)
    return INLINE_CODE_RE.sub(" ", base_cleaned)


def match_line(rel: str, line: str, max_tier: int, lang_filter: str) -> list[TermRule]:
    base_cleaned = URL_RE.sub("", MD_LINK_TARGET_RE.sub("]()", line))
    en_cleaned: str | None = None
    matched: list[TermRule] = []

    for rule in RULES:
        if rule.tier > max_tier:
            continue
        if lang_filter != "all" and rule.lang != lang_filter:
            continue

        if rule.lang == "zh":
            if rule.term not in base_cleaned:
                continue
            if rule.whitelist_re and rule.whitelist_re.search(base_cleaned):
                remainder = rule.whitelist_re.sub("", base_cleaned)
                if rule.term not in remainder:
                    continue
            matched.append(rule)
        else:
            if en_cleaned is None:
                en_cleaned = extract_english_prose_target(rel, base_cleaned)
            if not en_cleaned:
                continue
            assert rule.pattern_re is not None
            if not rule.pattern_re.search(en_cleaned):
                continue
            if rule.whitelist_re and rule.whitelist_re.search(en_cleaned):
                remainder = rule.whitelist_re.sub("", en_cleaned)
                if not rule.pattern_re.search(remainder):
                    continue
            matched.append(rule)

    return matched


def git_out(rdir: Path, args: list[str]) -> str:
    res = subprocess.run(
        ["git", "-C", str(rdir), *args],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    return res.stdout if res.returncode == 0 else ""


def walk_plain_dir(base: Path) -> list[str]:
    out: list[str] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DISCOVERY_DIRS and not d.startswith(".")]
        rel_root = Path(root).relative_to(base)
        for f in files:
            rel = (rel_root / f).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            out.append(rel)
    return sorted(out)


def collect_candidate_files(
    repo: str, rdir: Path, mode: str, since_spec: str | None, subrepo_rels: set[str]
) -> list[str]:
    if mode == "full":
        tracked = set(git_out(rdir, ["ls-files"]).splitlines())
        untracked = set(git_out(rdir, ["ls-files", "--others", "--exclude-standard"]).splitlines())
        files = sorted(tracked | untracked)
    elif mode == "since":
        assert since_spec is not None
        rev_check = subprocess.run(
            ["git", "-C", str(rdir), "rev-parse", "--verify", "--quiet", since_spec],
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_check.returncode == 0:
            logged = set(git_out(rdir, ["diff", "--name-only", f"{since_spec}...HEAD"]).splitlines())
        else:
            logged = set(git_out(rdir, ["log", f"--since={since_spec}", "--name-only", "--pretty=format:"]).splitlines())
        dirty = set()
        for sl in git_out(rdir, ["status", "--porcelain"]).splitlines():
            if len(sl) > 3:
                path_part = sl[3:].strip()
                if " -> " in path_part:
                    path_part = path_part.split(" -> ", 1)[1]
                dirty.add(path_part)
        files = sorted(f for f in (logged | dirty) if f)
    else:
        files = []

    result = []
    for f in files:
        if is_excluded_relpath(repo, f, subrepo_rels):
            continue
        full = rdir / f
        if full.is_file() and not full.is_symlink():
            result.append(f)
    return result


def passes_path_filter(repo: str, rel: str, path_filters: list[str]) -> bool:
    if not path_filters:
        return True
    combined = f"{repo}/{rel}" if repo != "." else rel
    for pf in path_filters:
        if pf in combined or pf in rel or fnmatch.fnmatch(combined, pf) or fnmatch.fnmatch(rel, pf):
            return True
    return False


def make_finding(repo: str, rel: str, line_no: int, content: str, matched: list[TermRule]) -> dict:
    display_path = rel if repo == "." else f"{repo}/{rel}"
    kind = classify_file(rel, content)
    return {
        "repo": repo,
        "file": rel,
        "display_path": display_path,
        "line": line_no,
        "kind": kind,
        "tier": min(r.tier for r in matched),
        "terms": [{"term": r.term, "lang": r.lang, "tier": r.tier, "suggestion": r.suggestion} for r in matched],
        "snippet": content.strip()[:140],
    }


def scan_single_file(
    repo: str,
    rel: str,
    full: Path,
    max_tier: int,
    lang_filter: str,
    allowed_lines: set[str] | None = None,
) -> list[dict]:
    try:
        text = full.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    out: list[dict] = []
    for idx, line in enumerate(text.splitlines(), 1):
        if allowed_lines is not None and line not in allowed_lines:
            continue
        matched = match_line(rel, line, max_tier, lang_filter)
        if matched:
            out.append(make_finding(repo, rel, idx, line, matched))
    return out


def scan_diff_mode(
    target_repos: dict[str, Path],
    subrepo_rels: set[str],
    path_filters: list[str],
    max_tier: int,
    lang_filter: str,
) -> list[dict]:
    findings: list[dict] = []
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for repo, rdir in target_repos.items():
        has_head = (
            subprocess.run(
                ["git", "-C", str(rdir), "rev-parse", "--verify", "--quiet", "HEAD"],
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        diff_args = ["diff", "HEAD", "-U0", "--no-color"] if has_head else ["diff", "-U0", "--no-color"]
        diff_txt = git_out(rdir, diff_args)
        cur_file: str | None = None
        cur_line = 0
        for raw in diff_txt.splitlines():
            if raw.startswith("+++ b/"):
                cur_file = raw[6:].strip()
                if is_excluded_relpath(repo, cur_file, subrepo_rels) or not passes_path_filter(repo, cur_file, path_filters):
                    cur_file = None
                continue
            if raw.startswith("+++ /dev/null"):
                cur_file = None
                continue
            m = hunk_re.match(raw)
            if m:
                cur_line = int(m.group(1))
                continue
            if cur_file is None:
                continue
            if raw.startswith("+") and not raw.startswith("+++"):
                content = raw[1:]
                matched = match_line(cur_file, content, max_tier, lang_filter)
                if matched:
                    findings.append(make_finding(repo, cur_file, cur_line, content, matched))
                cur_line += 1

        for uf in git_out(rdir, ["ls-files", "--others", "--exclude-standard"]).splitlines():
            if is_excluded_relpath(repo, uf, subrepo_rels) or not passes_path_filter(repo, uf, path_filters):
                continue
            full = rdir / uf
            if not full.is_file() or full.is_symlink():
                continue
            findings.extend(scan_single_file(repo, uf, full, max_tier, lang_filter))
    return findings


def collect_since_added_lines(
    repo: str, rdir: Path, since_spec: str, subrepo_rels: set[str]
) -> dict[str, set[str] | None]:
    file_lines: dict[str, set[str] | None] = {}
    rev_check = subprocess.run(
        ["git", "-C", str(rdir), "rev-parse", "--verify", "--quiet", since_spec],
        capture_output=True,
        text=True,
        check=False,
    )
    if rev_check.returncode == 0:
        patch_sources = [git_out(rdir, ["diff", f"{since_spec}...HEAD", "-U0", "--no-color"])]
    else:
        patch_sources = [git_out(rdir, ["log", f"--since={since_spec}", "-p", "-U0", "--no-color", "--pretty=format:"])]
    patch_sources.append(git_out(rdir, ["diff", "HEAD", "-U0", "--no-color"]))

    for patch_txt in patch_sources:
        cur_file: str | None = None
        for raw in patch_txt.splitlines():
            if raw.startswith("+++ b/"):
                cur_file = raw[6:].strip()
                if is_excluded_relpath(repo, cur_file, subrepo_rels):
                    cur_file = None
                continue
            if raw.startswith("+++ /dev/null"):
                cur_file = None
                continue
            if cur_file is not None and raw.startswith("+") and not raw.startswith("+++"):
                s = file_lines.setdefault(cur_file, set())
                if s is not None:
                    s.add(raw[1:])

    for uf in git_out(rdir, ["ls-files", "--others", "--exclude-standard"]).splitlines():
        if not is_excluded_relpath(repo, uf, subrepo_rels):
            file_lines[uf] = None
    return file_lines


def select_repos(all_repos: dict[str, Path], requested: list[str] | None) -> dict[str, Path]:
    if not requested:
        return all_repos
    selected: dict[str, Path] = {}
    for req in requested:
        req_norm = req.strip("/") or "."
        if req_norm in all_repos:
            selected[req_norm] = all_repos[req_norm]
        else:
            matches = [k for k in all_repos if Path(k).name == req_norm]
            for m in matches:
                selected[m] = all_repos[m]
    if not selected:
        available = ", ".join(all_repos.keys()) or "(none)"
        raise SystemExit(f"Unknown --repo {requested!r}. Discovered repos: {available}")
    return selected


def cmd_scan(args: argparse.Namespace) -> int:
    base, discovered_repos, subrepo_rels = resolve_workspace(args.root)
    max_tier = 1 if args.tier == "1" else 2
    lang_filter = args.lang
    path_filters = args.path or []

    if not discovered_repos:
        mode_desc = f"plain-directory full scan ({base})"
        findings: list[dict] = []
        for rel in walk_plain_dir(base):
            if is_excluded_relpath(".", rel, set()) or not passes_path_filter(".", rel, path_filters):
                continue
            full = base / rel
            if full.is_file() and not full.is_symlink():
                findings.extend(scan_single_file(".", rel, full, max_tier, lang_filter))
        target_labels = [str(base)]
    else:
        target_repos = select_repos(discovered_repos, args.repo)
        target_labels = list(target_repos.keys())
        if args.diff:
            mode_desc = "diff (uncommitted + untracked lines)"
            findings = scan_diff_mode(target_repos, subrepo_rels, path_filters, max_tier, lang_filter)
        elif args.full:
            mode_desc = "full (all mutable tracked + untracked files)"
            findings = []
            for repo, rdir in target_repos.items():
                for rel in collect_candidate_files(repo, rdir, "full", None, subrepo_rels):
                    if not passes_path_filter(repo, rel, path_filters):
                        continue
                    findings.extend(scan_single_file(repo, rel, rdir / rel, max_tier, lang_filter))
        elif args.whole_file:
            since_val = args.since or "14.days"
            mode_desc = f"since-whole-file ({since_val} + dirty working tree)"
            findings = []
            for repo, rdir in target_repos.items():
                for rel in collect_candidate_files(repo, rdir, "since", since_val, subrepo_rels):
                    if not passes_path_filter(repo, rel, path_filters):
                        continue
                    findings.extend(scan_single_file(repo, rel, rdir / rel, max_tier, lang_filter))
        else:
            since_val = args.since or "14.days"
            mode_desc = f"since-added-lines ({since_val} + dirty working tree)"
            findings = []
            for repo, rdir in target_repos.items():
                added_map = collect_since_added_lines(repo, rdir, since_val, subrepo_rels)
                for rel in sorted(added_map):
                    if not passes_path_filter(repo, rel, path_filters):
                        continue
                    full = rdir / rel
                    if not full.is_file() or full.is_symlink():
                        continue
                    findings.extend(
                        scan_single_file(repo, rel, full, max_tier, lang_filter, allowed_lines=added_map[rel])
                    )

    if args.json:
        print(
            json.dumps(
                {
                    "workspace": str(base),
                    "mode": mode_desc,
                    "lang": lang_filter,
                    "repos": target_labels,
                    "total_findings": len(findings),
                    "tier1_findings": sum(1 for f in findings if f["tier"] == 1),
                    "tier2_findings": sum(1 for f in findings if f["tier"] == 2),
                    "code_or_ui_findings": sum(1 for f in findings if f["kind"] == "code_or_ui"),
                    "findings": findings[: args.limit] if args.limit else findings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    t1 = sum(1 for f in findings if f["tier"] == 1)
    t2 = sum(1 for f in findings if f["tier"] == 2)
    code_ui = sum(1 for f in findings if f["kind"] == "code_or_ui")
    docs_comments = len(findings) - code_ui

    print(f"=== Plain-Language Scan [{mode_desc} | lang={lang_filter}] ===")
    print(f"Workspace: {base} | Repos: {', '.join(target_labels)}")
    print(
        f"Total hits: {len(findings)} "
        f"(Tier-1 must-replace: {t1}, Tier-2 context-dependent: {t2} | docs/comments: {docs_comments}, runtime/UI strings: {code_ui})"
    )
    if not findings:
        print("OK: No jargon findings.")
        return 0

    print("")
    shown = findings[: args.limit] if args.limit else findings
    for item in shown:
        tags = ", ".join(f"[T{t['tier']}:{t['lang'].upper()}]{t['term']} -> {t['suggestion']}" for t in item["terms"])
        kind_flag = " [check test assertions]" if item["kind"] == "code_or_ui" else ""
        print(f"- {item['display_path']}:{item['line']}{kind_flag}")
        print(f"  Match: {tags}")
        print(f"  Text:  {item['snippet']}")

    if args.limit and len(findings) > args.limit:
        print(f"\n... {len(findings) - args.limit} more findings omitted (increase --limit or narrow with --repo / --path)")
    return 0


def is_strictly_forbidden_touch(rel: str, status_xy: str) -> str | None:
    rel_norm = rel.strip().replace("\\", "/")
    if rel_norm in {"branches.yaml", "CHANGELOG.md", "VERSION"}:
        return f"locked version/branch file ({rel_norm})"
    if rel_norm.startswith(FORBIDDEN_PREFIXES):
        return f"frozen contract or historical archive directory ({rel_norm})"
    padded = "/" + rel_norm
    if "/archive/" in padded and status_xy != "??":
        return f"committed archive file ({rel_norm})"
    if rel_norm.endswith((".sql", ".pb.go")):
        return f"immutable SQL migration or generated protobuf file ({Path(rel_norm).suffix})"
    return None


def cmd_verify(args: argparse.Namespace) -> int:
    base, discovered_repos, subrepo_rels = resolve_workspace(args.root)
    if not discovered_repos:
        print(f"Workspace {base} is not a Git repository; run `scan --full` instead.")
        return 0

    target_repos = select_repos(discovered_repos, args.repo)
    path_filters = args.path or []
    lang_filter = args.lang
    violations: list[tuple[str, str, str]] = []
    sync_hints: list[str] = []

    for repo, rdir in target_repos.items():
        for sl in git_out(rdir, ["status", "--porcelain"]).splitlines():
            if len(sl) <= 3:
                continue
            status_xy = sl[:2]
            f = sl[3:].strip()
            if " -> " in f:
                f = f.split(" -> ", 1)[1]
            if path_filters and not passes_path_filter(repo, f, path_filters):
                continue
            reason = is_strictly_forbidden_touch(f, status_xy)
            if reason:
                violations.append((repo, f, reason))
            hint = GENERATED_BASENAME_HINTS.get(Path(f).name)
            if hint and status_xy != "??":
                disp = f if repo == "." else f"{repo}/{f}"
                sync_hints.append(f"{disp}: {hint}")

    print("=== 1. Forbidden File Boundary Check ===")
    if violations:
        for repo, f, reason in violations:
            disp = f if repo == "." else f"{repo}/{f}"
            print(f"FAIL: Forbidden modification: {disp} -- {reason}")
        return 1
    print(
        f"OK: 0 forbidden files touched across {len(target_repos)} repo(s) "
        "(CHANGELOG / VERSION / committed archives / contracts / *.sql / *.pb.go)"
    )

    if sync_hints:
        print("\n=== 2. Generated Artifact Sync Notices ===")
        for h in sync_hints:
            print(f"NOTE: {h}")

    print(f"\n=== 3. Added-Lines Tier-1 Jargon Re-check [lang={lang_filter}] ===")
    diff_t1 = scan_diff_mode(target_repos, subrepo_rels, path_filters, max_tier=1, lang_filter=lang_filter)
    if diff_t1:
        print(f"FAIL: Uncommitted added lines still contain {len(diff_t1)} Tier-1 jargon hit(s):")
        for item in diff_t1[:20]:
            terms = "/".join(f"{t['lang'].upper()}:{t['term']}" for t in item["terms"])
            print(f"  - {item['display_path']}:{item['line']} [{terms}] {item['snippet']}")
        return 1
    print("OK: 0 Tier-1 jargon hits in uncommitted added lines")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Plain-language bilingual (ZH + EN) jargon scanner & boundary verifier")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Scan files or diffs for Chinese & English corporate/AI jargon")
    p_scan.add_argument("--root", default=".", help="Workspace or Git repository root (default: current directory)")
    mode = p_scan.add_mutually_exclusive_group()
    mode.add_argument("--since", help="Scan added/modified lines since git time/rev (default: 14.days)")
    mode.add_argument("--diff", action="store_true", help="Scan only uncommitted added lines (+ lines) across repos")
    mode.add_argument("--full", action="store_true", help="Scan all mutable tracked/untracked files across repos")
    p_scan.add_argument("--whole-file", action="store_true", help="With --since, scan entire touched files instead of only added lines")
    p_scan.add_argument("--repo", action="append", help="Target discovered repo(s); repeatable (default: all discovered)")
    p_scan.add_argument("--path", action="append", help="Filter by path substring or glob; repeatable")
    p_scan.add_argument("--tier", choices=["1", "all"], default="all", help="1 = high-certainty jargon only; all = Tier 1 + Tier 2")
    p_scan.add_argument("--lang", choices=["all", "zh", "en"], default="all", help="Filter vocabulary language (default: all)")
    p_scan.add_argument("--limit", type=int, default=80, help="Max findings printed (0 = unlimited, default: 80)")
    p_scan.add_argument("--json", action="store_true", help="Output structured JSON")
    p_scan.set_defaults(func=cmd_scan)

    p_verify = sub.add_parser("verify", help="Verify zero forbidden files touched and zero Tier-1 jargon in added lines")
    p_verify.add_argument("--root", default=".", help="Workspace or Git repository root (default: current directory)")
    p_verify.add_argument("--repo", action="append", help="Target discovered repo(s); repeatable (default: all discovered)")
    p_verify.add_argument("--path", action="append", help="Filter by path substring or glob; repeatable")
    p_verify.add_argument("--lang", choices=["all", "zh", "en"], default="all", help="Filter vocabulary language (default: all)")
    p_verify.set_defaults(func=cmd_verify)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
