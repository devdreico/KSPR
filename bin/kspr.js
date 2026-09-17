#!/usr/bin/env node
// KSPR CLI - Node.js wrapper
// Installed globally via: npm install -g kspr-ai
// Or locally: npx kspr-ai

const { spawn } = require("child_process");
const path = require("path");

const pythonScript = path.join(__dirname, "..", "cli", "kspr.py");

// Use python3 directly (works in most environments)
const pythonCmd = process.platform === "win32" ? "python" : "python3";

const args = [pythonScript, ...process.argv.slice(2)];

const child = spawn(pythonCmd, args, { stdio: "inherit" });

child.on("error", (err) => {
  console.error("KSPR CLI Error:", err.message);
  console.error("Ensure Python 3 and KSPR dependencies are installed (pip install -e .).");
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code !== null ? code : 0);
});