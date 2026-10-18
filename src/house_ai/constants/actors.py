"""Actor constants, including disallowed prefixes and IDs for human actors."""

DISALLOWED_HUMAN_PREFIXES: tuple[str, ...] = ("agent:", "system:")

KNOWN_AGENT_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "agent",
        "system",
        "gemini",
        "claude-code",
        "codex",
        "chatgpt",
        "antigravity",
        "cursor",
        "copilot",
        "openai",
        "anthropic",
    }
)
