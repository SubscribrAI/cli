#!/usr/bin/env node

const { spawnSync } = require("child_process");
const path = require("path");

const cli = path.join(__dirname, "..", "subscribr.py");
const result = spawnSync(process.env.PYTHON || "python3", [cli, ...process.argv.slice(2)], {
  stdio: "inherit",
});

if (result.error) {
  console.error(`Unable to launch Subscribr CLI: ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
