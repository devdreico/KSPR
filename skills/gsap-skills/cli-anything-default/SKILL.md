---
name: cli-anything-default
description: Guide for using the KSPR AI CLI TOOL Capability Layer
category: core
version: 0.1.0
---

# Capability Layer — Guide for KSPR AI CLI TOOL

You are the KSPR AI CLI TOOL agent. You have access to a Capability Layer that lets you discover and execute external tools installed on the system.

## How It Works

The Capability Layer discovers installed command-line tools and presents them as traceable capabilities that you can inspect and execute with explicit permissions.

### Usage Flow

1. **Discover** available capabilities with `/capabilities`
2. **View** details with `/capabilities info <id>`
3. **Execute** with `/capabilities run <id> --key=value`

## Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/capabilities` | List all capabilities | `/capabilities` |
| `/capabilities search <query>` | Search by name/description | `/capabilities search analysis` |
| `/capabilities info <id>` | Detailed capability info | `/capabilities info cli-any:code-analysis` |
| `/capabilities run <id> [args]` | Execute a capability | `/capabilities run cli-any:code-analysis --file=src/main.py` |
| `/capabilities skill <id>` | Show SKILL.md of a capability | `/capabilities skill cli-any:code-analysis` |
| `/capabilities refresh` | Refresh the catalog | `/capabilities refresh` |

## Argument Format

Arguments are passed as `--key=value` after the capability ID:

```
/capabilities run cli-any:analyze --file=src/main.py --format=json
```

Boolean flags are passed without value:
```
/capabilities run cli-any:lint --verbose
```

## Error Handling

If a capability fails, check:
1. The exit code
2. The error message in stderr
3. Use `/capabilities info <id>` to verify the capability is installed

## Permissions

Each capability has a permission level:
- **read**: Read-only info access
- **execute**: Basic execution (requires confirmation)
- **write**: Filesystem write
- **admin**: Administrative operations

## Rules for KSPR I

1. Always use `/capabilities` to discover available tools before attempting execution.
2. Read the SKILL.md of any capability before using it for the first time.
3. Pass arguments using `--key=value` format after the capability ID.
4. Check the exit code and stderr if a capability fails.
5. Use `--json` flag when available for structured output.
6. Never guess capability IDs — always discover them first.
7. Respect permission levels — prompt the user when needed.
