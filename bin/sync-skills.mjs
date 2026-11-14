#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SELF_REPO = "kilingzhang/skills";
const ROOT_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SKILLS_DIR = join(ROOT_DIR, "skills");
const REMOTE_MANIFEST = join(ROOT_DIR, "remote-skills.json");

function printHelp() {
  console.log(`Usage: npx github:${SELF_REPO} [options]

Install first-party skills from ${SELF_REPO} and upstream skills declared in
remote-skills.json directly from their original repositories via npx skills.

Options:
  -g, --global              Install globally (default)
  -p, --project             Install into the current project instead of globally
  -a, --agent <agents...>   Target specific agents (forwarded to npx skills add)
  -s, --skill <names...>    Install only matching skill names
      --only <names...>     Alias for --skill
      --local-only          Install only first-party skills from ${SELF_REPO}
      --remote-only         Install only upstream skills from remote-skills.json
      --copy                Copy files instead of symlinking
      --list                Show configured first-party and upstream skills
      --dry-run             Print commands without executing them
  -h, --help                Show this help message

Updates:
  Once installed, run "npx skills update" to pull updates directly from each
  skill's upstream repository.
`);
}

function collectValues(argv, startIndex) {
  const values = [];
  let i = startIndex + 1;
  while (i < argv.length && !argv[i].startsWith("-")) {
    for (const part of argv[i].split(",")) {
      const trimmed = part.trim();
      if (trimmed) values.push(trimmed);
    }
    i += 1;
  }
  return { values, nextIndex: i - 1 };
}

function parseArgs(argv) {
  const opts = {
    global: true,
    agents: [],
    skills: [],
    localOnly: false,
    remoteOnly: false,
    copy: false,
    list: false,
    dryRun: false,
    help: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--") continue;
    if (arg === "-h" || arg === "--help") {
      opts.help = true;
    } else if (arg === "-g" || arg === "--global") {
      opts.global = true;
    } else if (arg === "-p" || arg === "--project") {
      opts.global = false;
    } else if (arg === "--local-only") {
      opts.localOnly = true;
    } else if (arg === "--remote-only") {
      opts.remoteOnly = true;
    } else if (arg === "--copy") {
      opts.copy = true;
    } else if (arg === "--list") {
      opts.list = true;
    } else if (arg === "--dry-run") {
      opts.dryRun = true;
    } else if (arg === "-a" || arg === "--agent") {
      const { values, nextIndex } = collectValues(argv, i);
      if (values.length === 0) {
        throw new Error(`${arg} requires at least one agent name`);
      }
      opts.agents.push(...values);
      i = nextIndex;
    } else if (arg === "-s" || arg === "--skill" || arg === "--only") {
      const { values, nextIndex } = collectValues(argv, i);
      if (values.length === 0) {
        throw new Error(`${arg} requires at least one skill name`);
      }
      opts.skills.push(...values);
      i = nextIndex;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }

  if (opts.localOnly && opts.remoteOnly) {
    throw new Error("--local-only and --remote-only cannot be used together");
  }

  return opts;
}

function getLocalSkills() {
  if (!existsSync(SKILLS_DIR)) return [];
  return readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => existsSync(join(SKILLS_DIR, name, "SKILL.md")))
    .sort();
}

function getRemoteEntries() {
  if (!existsSync(REMOTE_MANIFEST)) return [];
  const raw = JSON.parse(readFileSync(REMOTE_MANIFEST, "utf-8"));
  const entries = Array.isArray(raw.remotes) ? raw.remotes : [];
  for (const entry of entries) {
    if (!entry || typeof entry.source !== "string" || !entry.source.trim()) {
      throw new Error("Each entry in remote-skills.json must define a non-empty 'source' string");
    }
  }
  return entries;
}

function formatSourceWithRef(entry) {
  const source = entry.source.trim();
  if (entry.ref && typeof entry.ref === "string" && !source.includes("#")) {
    return `${source}#${entry.ref.trim()}`;
  }
  return source;
}

function buildAddArgs(source, skillNames, opts) {
  const args = ["--yes", "skills", "add", source];
  if (opts.global) args.push("-g");
  if (opts.agents.length > 0) args.push("-a", ...opts.agents);
  if (skillNames && skillNames.length > 0) {
    args.push("-s", ...skillNames);
  } else {
    args.push("-s", "*");
  }
  if (opts.copy) args.push("--copy");
  args.push("-y");
  return args;
}

function runSkillsAdd(source, skillNames, opts) {
  const args = buildAddArgs(source, skillNames, opts);
  const printable = `npx ${args.map((a) => (a === "*" ? "'*'" : a)).join(" ")}`;
  console.log(`> ${printable}`);
  if (opts.dryRun) return;

  const result = spawnSync("npx", args, { stdio: "inherit" });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }

  if (opts.help) {
    printHelp();
    return;
  }

  const localSkills = getLocalSkills();
  const remoteEntries = getRemoteEntries();

  if (opts.list) {
    console.log(`First-party skills (${SELF_REPO}):`);
    for (const name of localSkills) {
      console.log(`  - ${name}`);
    }
    console.log("\nReferenced upstream skills (remote-skills.json):");
    for (const entry of remoteEntries) {
      const names = Array.isArray(entry.skills) && entry.skills.length > 0 ? entry.skills.join(", ") : "*";
      console.log(`  - ${names} <- ${formatSourceWithRef(entry)}`);
    }
    return;
  }

  const filterSet = opts.skills.length > 0 ? new Set(opts.skills) : null;
  let ranAny = false;

  if (!opts.remoteOnly && localSkills.length > 0) {
    const selectedLocal = filterSet
      ? localSkills.filter((name) => filterSet.has(name))
      : ["*"];
    if (selectedLocal.length > 0) {
      runSkillsAdd(SELF_REPO, selectedLocal, opts);
      ranAny = true;
    }
  }

  if (!opts.localOnly && remoteEntries.length > 0) {
    for (const entry of remoteEntries) {
      const declared = Array.isArray(entry.skills) && entry.skills.length > 0 ? entry.skills : null;
      let selectedRemote;
      if (filterSet) {
        if (!declared) continue;
        selectedRemote = declared.filter((name) => filterSet.has(name));
        if (selectedRemote.length === 0) continue;
      } else {
        selectedRemote = declared ?? ["*"];
      }
      runSkillsAdd(formatSourceWithRef(entry), selectedRemote, opts);
      ranAny = true;
    }
  }

  if (!ranAny) {
    console.error("No matching skills found to install.");
    process.exit(1);
  }

  if (!opts.dryRun) {
    console.log("\nDone. Run 'npx skills update' anytime to pull updates directly from each upstream source.");
  }
}

main();
