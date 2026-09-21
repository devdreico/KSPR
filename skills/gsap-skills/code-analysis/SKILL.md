---
name: code-analysis
description: KSPR AI CLI TOOL skills for code quality analysis
category: analysis
version: 0.1.0
---

# Code Analysis Skills for KSPR AI CLI TOOL

Structured checks for code quality, complexity, duplication, and maintainability. Results can be used as evidence in a reconstructed technical context.

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `analyze <file>` | Analyze a file for code smells | `analyze src/main.py` |
| `lint <dir>` | Run linter on a directory | `lint src/` |
| `complexity <file>` | Calculate complexity metrics | `complexity src/utils.py` |
| `duplicates <dir>` | Detect duplicate code | `duplicates src/` |
| `report` | Generate full quality report | `report --format=json` |

## Metrics

- **Cyclomatic Complexity**: Per-function cyclomatic complexity
- **Lines of Code**: Effective lines of code
- **Duplication %**: Percentage of duplicate code
- **Maintainability Index**: Maintainability score
