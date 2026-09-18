---
name: security-audit
description: Source code security audit tools
category: security
version: 0.1.0
---

# Security Audit Skills

Tools for detecting vulnerabilities and security issues.

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `audit <dir>` | Full security audit | `audit src/` |
| `scan <file>` | Quick vulnerability scan | `scan src/auth.py` |
| `secrets <dir>` | Find hardcoded secrets | `secrets src/` |
| `deps` | Analyze vulnerable dependencies | `deps` |
| `report` | Generate security report | `report --format=json` |

## Vulnerability Categories

- **Injection**: SQL, XSS, Command injection
- **Authentication**: Authentication issues
- **Authorization**: Permission bypass
- **Secrets**: Hardcoded keys, tokens, passwords
- **Dependencies**: Dependencies with known CVEs
