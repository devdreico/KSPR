#!/usr/bin/env node
// KSPR CLI - Node.js wrapper.
// Installed globally via: npm install -g kspr-ai
// Or locally: npx kspr-ai

const { spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const repoRoot = path.join(__dirname, "..");
const pythonScript = path.join(repoRoot, "cli", "kspr.py");

const venvPython = process.platform === "win32"
  ? path.join(repoRoot, ".venv", "Scripts", "python.exe")
  : path.join(repoRoot, ".venv", "bin", "python");

const pythonCmd = fs.existsSync(venvPython)
  ? venvPython
  : (process.platform === "win32" ? "python" : "python3");

const result = spawnSync(pythonCmd, [pythonScript, ...process.argv.slice(2)], { stdio: "inherit" });

if (result.error) {
  console.error("KSPR CLI Error:", result.error.message);
  console.error("Ensure Python 3 and KSPR dependencies are installed (pip install -e .).");
  process.exit(1);
}

process.exit(result.status === null ? 1 : result.status);
