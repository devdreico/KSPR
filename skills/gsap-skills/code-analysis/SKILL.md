---
name: code-analysis
description: Code quality analysis tools
category: analysis
version: 0.1.0
---

# Code Analysis Skills

Tools for analyzing code quality, complexity, and style.

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
