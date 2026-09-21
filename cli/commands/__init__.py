"""Command layer for the KSPR interactive shell."""

from .registry import COMMANDS, Command, find_command, fuzzy_score, search_commands

__all__ = ["COMMANDS", "Command", "find_command", "fuzzy_score", "search_commands"]
