const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const ROOT = path.resolve(__dirname, "..");
const INSTALLER = path.join(ROOT, "bin", "install.js");

test("ships a portable Agent Plugins manifest without embedding MCP credentials", () => {
  const plugin = JSON.parse(fs.readFileSync(path.join(ROOT, "plugin.json"), "utf8"));
  const packageJson = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));

  assert.equal(plugin.$schema, "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json");
  assert.equal(plugin.name, "subscribr-cli");
  assert.equal(plugin.version, packageJson.version);
  assert.equal(fs.existsSync(path.join(ROOT, "mcp.json")), false);
  assert.equal(fs.existsSync(path.join(ROOT, "skills", "subscribr-api", "SKILL.md")), true);
});

function project() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "subscribr-cli-install-"));
}

function install(cwd, ...args) {
  return spawnSync(process.execPath, [INSTALLER, ...args], {
    cwd,
    encoding: "utf8",
  });
}

function runCli(bundle, ...args) {
  return spawnSync("python3", [path.join(bundle, "subscribr.py"), ...args], {
    encoding: "utf8",
  });
}

test("replaces installer-owned skill directories so stale generated files disappear", (t) => {
  const cwd = project();
  t.after(() => fs.rmSync(cwd, { recursive: true, force: true }));
  const stale = path.join(cwd, ".agents", "skills", "subscribr-api", "references", "stale.md");
  fs.mkdirSync(path.dirname(stale), { recursive: true });
  fs.writeFileSync(stale, "obsolete");

  const result = install(cwd);

  assert.equal(result.status, 0, result.stderr);
  assert.equal(fs.existsSync(stale), false);
  assert.equal(fs.existsSync(path.join(cwd, ".agents", "skills", "subscribr-api", "references", "operations.json")), true);
  assert.equal(fs.existsSync(path.join(cwd, ".claude", "skills", "subscribr-api", "references", "operations.json")), true);
});

test("refuses to overwrite an existing default CLI without force", (t) => {
  const cwd = project();
  t.after(() => fs.rmSync(cwd, { recursive: true, force: true }));
  const destination = path.join(cwd, ".subscribr-cli");
  const sentinel = path.join(destination, "keep-me");
  fs.mkdirSync(destination);
  fs.writeFileSync(sentinel, "keep me\n");

  const result = install(cwd, "--with-cli");

  assert.equal(result.status, 1);
  assert.match(result.stderr, /already exists; pass --force/i);
  assert.equal(fs.readFileSync(sentinel, "utf8"), "keep me\n");
});

test("rejects the deprecated file destination before changing the project", (t) => {
  const cwd = project();
  t.after(() => fs.rmSync(cwd, { recursive: true, force: true }));
  const sentinel = path.join(cwd, ".agents", "skills", "subscribr-api", "sentinel");
  fs.mkdirSync(path.dirname(sentinel), { recursive: true });
  fs.writeFileSync(sentinel, "keep me\n");

  const result = install(cwd, "--cli-path", "tools/subscribr.py");

  assert.equal(result.status, 1);
  assert.match(result.stderr, /--cli-path has been replaced by directory-based --cli-dir/i);
  assert.equal(fs.readFileSync(sentinel, "utf8"), "keep me\n");
  assert.equal(fs.existsSync(path.join(cwd, ".claude")), false);
});

test("installs a self-contained CLI bundle and only replaces it with force", (t) => {
  const cwd = project();
  t.after(() => fs.rmSync(cwd, { recursive: true, force: true }));
  const relativeDestination = "tools/subscribr-cli";
  const destination = path.join(cwd, relativeDestination);
  const cli = path.join(destination, "subscribr.py");
  const metadata = path.join(destination, "skills", "subscribr-api", "references", "operations.json");

  assert.equal(install(cwd, "--cli-dir", relativeDestination).status, 0);
  const installed = fs.readFileSync(cli, "utf8");
  assert.match(installed, /Zero-dependency CLI transport/);
  assert.equal(fs.existsSync(metadata), true);

  const version = runCli(destination, "version");
  assert.equal(version.status, 0, version.stderr);
  // Read the expected version from package.json rather than pinning it, so a
  // release bump does not need a test edit.
  const declaredVersion = JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "package.json"), "utf8"),
  ).version;
  assert.equal(version.stdout.trim(), declaredVersion);

  const help = runCli(destination, "help");
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /scripts/);
  assert.match(help.stdout, /operations/);
  assert.match(help.stdout, /video\s+\(32 actions\)/);

  const operationHelp = runCli(destination, "operations", "help");
  assert.equal(operationHelp.status, 0, operationHelp.stderr);
  assert.match(operationHelp.stdout, /get-operation/);
  assert.match(operationHelp.stdout, /\/api\/v1\/operations\/\{operation\}/);

  const videoHelp = runCli(destination, "video", "help");
  assert.equal(videoHelp.status, 0, videoHelp.stderr);
  assert.match(videoHelp.stdout, /list-capabilities/);
  assert.match(videoHelp.stdout, /get-channel/);
  assert.match(videoHelp.stdout, /required: --video-channel <value>/);
  assert.match(videoHelp.stdout, /get-media-asset/);
  assert.match(videoHelp.stdout, /required: --media-asset <value>/);
  assert.match(videoHelp.stdout, /apply-revision/);
  assert.match(videoHelp.stdout, /add-overlay/);
  assert.match(videoHelp.stdout, /quote-video/);
  assert.match(videoHelp.stdout, /create-video/);
  assert.match(videoHelp.stdout, /cancel-video/);

  const installedSkill = fs.readFileSync(
    path.join(cwd, ".agents", "skills", "subscribr-api", "SKILL.md"),
    "utf8",
  );
  assert.match(installedSkill, /video_capability_unavailable/);
  assert.match(installedSkill, /owner\/admin-only/);
  assert.match(installedSkill, /video apply-revision/);
  assert.match(installedSkill, /video:publish/);
  assert.match(installedSkill, /video:generate/);
  assert.match(installedSkill, /required_credits/);
  assert.match(installedSkill, /immutable/);

  fs.writeFileSync(cli, "custom\n");
  assert.equal(install(cwd, "--cli-dir", relativeDestination).status, 1);
  assert.equal(fs.readFileSync(cli, "utf8"), "custom\n");
  assert.equal(install(cwd, "--cli-dir", relativeDestination, "--force").status, 0);
  assert.equal(fs.readFileSync(cli, "utf8"), installed);
  assert.equal(fs.existsSync(metadata), true);
});
