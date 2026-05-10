"""Persisted Model Context Protocol (MCP) server configuration.

This module owns the on-disk catalogue of MCP servers the user has registered
with brodex. The actual runtime integration (spawning a server, discovering
its tools, surfacing them through the agent loop) lives elsewhere — this file
is purely about reading and writing `~/.brodex/mcp.json`.
"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".brodex"
CONFIG_PATH = CONFIG_DIR / "mcp.json"
SCHEMA_VERSION = 1


def _load() -> dict:
    if not CONFIG_PATH.exists():
        return {"version": SCHEMA_VERSION, "servers": {}}
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"version": SCHEMA_VERSION, "servers": {}}
    data.setdefault("version", SCHEMA_VERSION)
    data.setdefault("servers", {})
    return data


def _save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n")


def list_servers() -> dict[str, dict]:
    """Return a `{name: spec}` mapping of all registered MCP servers."""
    return _load().get("servers", {})


def add_server(
    name: str,
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    """Register or replace an MCP server. Returns the stored spec."""
    if not name:
        raise ValueError("MCP server name is required")
    if not command:
        raise ValueError("MCP server command is required")

    data = _load()
    spec = {
        "command": command,
        "args": list(args or []),
        "env": dict(env or {}),
    }
    data["servers"][name] = spec
    _save(data)
    return spec


def remove_server(name: str) -> bool:
    """Drop a server. Returns True if it existed, False otherwise."""
    data = _load()
    if name not in data["servers"]:
        return False
    del data["servers"][name]
    _save(data)
    return True


def config_path() -> Path:
    return CONFIG_PATH
