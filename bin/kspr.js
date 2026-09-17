#!/usr/bin/env node

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const pythonScript = path.join(__dirname, "..", "cli", "kspr.py");
const args = [pythonScript, ...process.argv.slice(2)];

const venvPython = path.join(__dirname, "..", ".venv", "bin", "python");
const pythonCmd = fs.existsSync(venvPython) ? venvPython : (process.platform === "win32" ? "python" : "python3");

const child = spawn(pythonCmd, args, { stdio: "inherit" });

child.on("error", (err) => {
  console.error("KSPR CLI Error:", err.message);
  console.error("Ensure Python 3 and KSPR dependencies are installed (pip install -e .).");
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code !== null ? code : 0);
});
