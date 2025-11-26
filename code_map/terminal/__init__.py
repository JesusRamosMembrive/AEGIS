"""
Terminal module for web-based shell access

Provides:
- PTY-based shell execution accessible via WebSocket
- Claude Code JSON streaming runner
- JSON event parser for Claude Code output
"""

from .pty_shell import PTYShell
from .claude_runner import ClaudeAgentRunner, ClaudeRunnerConfig
from .json_parser import JSONStreamParser, ClaudeEvent, EventType, EventSubtype

__all__ = [
    "PTYShell",
    "ClaudeAgentRunner",
    "ClaudeRunnerConfig",
    "JSONStreamParser",
    "ClaudeEvent",
    "EventType",
    "EventSubtype",
]
