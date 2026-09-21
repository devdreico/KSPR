---
name: security-audit
description: KSPR AI CLI TOOL skills for source code security audits
category: security
version: 0.1.0
---

# Security Audit Skills for KSPR AI CLI TOOL

Structured checks for common vulnerability classes and security evidence in source code and dependencies.

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
