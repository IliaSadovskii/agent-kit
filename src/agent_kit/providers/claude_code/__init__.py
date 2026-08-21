"""Claude Code, driven headless. What can be declared is in `provider.toml`."""

from .adapter import ClaudeCode, build_executor

__all__ = ["ClaudeCode", "build_executor"]
