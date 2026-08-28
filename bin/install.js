#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const SKILL_SRC = path.join(__dirname, "..", "skills", "subscribr-api");
const CLI_SRC = path.join(__dirname, "..", "subscribr.py");
const CLI_METADATA_SRC = path.join(SKILL_SRC, "references", "operations.json");

// Standard locations per Agent Skills spec + Claude Code
const AGENTS_DIR = path.join(process.cwd(), ".agents", "skills", "subscribr-api");
const CLAUDE_DIR = path.join(process.cwd(), ".claude", "skills", "subscribr-api");

function fail(message) {
  console.error(`Error: ${message}`);
  process.exit(1);
}

function optionValue(name) {
  const index = process.argv.indexOf(name);
  if (index === -1) return null;
  const value = process.argv[index + 1];
  if (!value || value.startsWith("--")) fail(`${name} requires a path.`);
  return value;
}

function pathExists(target) {
  try {
    fs.lstatSync(target);
    return true;
  } catch (error) {
    if (error && error.code === "ENOENT") return false;
    throw error;
  }
}

function replaceDirectory(src, dest, label) {
  const parent = path.dirname(dest);
  const temporary = path.join(parent, `.${path.basename(dest)}.tmp-${process.pid}`);
  const backup = path.join(parent, `.${path.basename(dest)}.backup-${process.pid}`);

  fs.mkdirSync(parent, { recursive: true });
  fs.rmSync(temporary, { recursive: true, force: true });
  fs.rmSync(backup, { recursive: true, force: true });
  fs.cpSync(src, temporary, { recursive: true, force: true });

  try {
    if (pathExists(dest)) fs.renameSync(dest, backup);
    fs.renameSync(temporary, dest);
    fs.rmSync(backup, { recursive: true, force: true });
  } catch (error) {
    fs.rmSync(temporary, { recursive: true, force: true });
    if (!pathExists(dest) && pathExists(backup)) fs.renameSync(backup, dest);
    throw error;
  }

  console.log(`  \u2713 ${label} \u2192 ${path.relative(process.cwd(), dest)}`);
}

function copyCliBundle(dest, force) {
  if (pathExists(dest) && !force) {
    fail(`${path.relative(process.cwd(), dest) || dest} already exists; pass --force to replace it or choose --cli-dir.`);
  }

  const parent = path.dirname(dest);
  const temporary = path.join(parent, `.${path.basename(dest)}.tmp-${process.pid}`);
  const backup = path.join(parent, `.${path.basename(dest)}.backup-${process.pid}`);
  const cli = path.join(temporary, "subscribr.py");
  const metadata = path.join(temporary, "skills", "subscribr-api", "references", "operations.json");

  fs.mkdirSync(parent, { recursive: true });
  fs.rmSync(temporary, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(metadata), { recursive: true });
  fs.rmSync(backup, { recursive: true, force: true });
  fs.copyFileSync(CLI_SRC, cli);
  fs.copyFileSync(CLI_METADATA_SRC, metadata);
  fs.chmodSync(cli, 0o755);

  try {
    if (pathExists(dest)) fs.renameSync(dest, backup);
    fs.renameSync(temporary, dest);
    fs.rmSync(backup, { recursive: true, force: true });
  } catch (error) {
    fs.rmSync(temporary, { recursive: true, force: true });
    if (!pathExists(dest) && pathExists(backup)) fs.renameSync(backup, dest);
    throw error;
  }

  console.log(`  \u2713 CLI bundle \u2192 ${path.relative(process.cwd(), dest)}`);
}

const withCli = process.argv.includes("--with-cli");
const cliDirectory = optionValue("--cli-dir");
if (process.argv.includes("--cli-path")) fail("--cli-path has been replaced by directory-based --cli-dir.");
const force = process.argv.includes("--force");
const cliDestination = withCli || cliDirectory
  ? path.resolve(process.cwd(), cliDirectory || ".subscribr-cli")
  : null;

console.log("\n  @subscribrai/cli\n");

// These directories are installer-owned. Replacing them atomically avoids old
// generated references surviving a contract update.
replaceDirectory(SKILL_SRC, AGENTS_DIR, "Skill (.agents/skills/)");

replaceDirectory(SKILL_SRC, CLAUDE_DIR, "Skill (.claude/skills/)");

// Install the optional self-contained CLI bundle only when explicitly
// requested. Its colocated generated metadata is required by subscribr.py.
if (cliDestination) {
  copyCliBundle(cliDestination, force);
}

console.log("\n  Setup:\n");
console.log("  1. Get a Team-bound API token at https://subscribr.ai/integrations");
console.log("  2. export SUBSCRIBR_API_TOKEN=...");
console.log("  3. subscribr doctor            # confirms the token, Team, and plan\n");

if (cliDestination) {
  const cli = path.relative(process.cwd(), path.join(cliDestination, "subscribr.py"));
  console.log("  CLI usage:\n");
  console.log(`  python3 ${cli} help`);
  console.log(`  python3 ${cli} scripts create-channel-script --help\n`);
} else {
  console.log("  To also install the Python CLI:");
  console.log("  subscribr-install-skill --with-cli [--cli-dir directory] [--force]\n");
}

console.log("  Discovery:\n");
console.log("  subscribr help                          # domains");
console.log("  subscribr <domain> help                 # actions and required flags");
console.log("  subscribr <domain> <action> --help      # fields, ranges, example body\n");
console.log("  Docs: https://subscribr.ai/youtube-api");
console.log("  API ref: curl -s https://subscribr.ai/api/docs/reference/ai\n");
