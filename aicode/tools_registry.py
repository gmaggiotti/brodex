from pathlib import Path

from aicode.tools.code_tools import edit_file as _edit_file_tool
from aicode.tools.code_tools import execute_command as _execute_command_tool
from aicode.tools import read_file, search_web, fetch_url


async def _tool_read_file(path: str) -> str:
    return read_file(path)


async def _tool_execute_command(command: str) -> str:
    return await _execute_command_tool(command)


async def _tool_search_web(query: str) -> str:
    return await search_web(query)


async def _tool_fetch_url(url: str) -> str:
    return await fetch_url(url)


async def _tool_edit_file(path: str, old_text: str, new_text: str) -> str:
    return await _edit_file_tool(path, old_text, new_text)


async def _tool_create_file(path: str, content: str) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Created {path} ({len(content)} chars)"


TOOLS = {
    "read_file": {
        "description": "Read the contents of a file.",
        "params": {"path": "file path"},
        "modifies_fs": False,
        "fn": _tool_read_file,
    },
    "execute_command": {
        "description": (
            "Run a read-only shell command (ls, find, grep, git status/log/diff, "
            "cat, head, tail, etc.) and return its output. Do NOT use for "
            "destructive commands — use edit_file or create_file for changes."
        ),
        "params": {"command": "shell command"},
        "modifies_fs": False,
        "fn": _tool_execute_command,
    },
    "search_web": {
        "description": "Run a web search and return top results.",
        "params": {"query": "search query"},
        "modifies_fs": False,
        "fn": _tool_search_web,
    },
    "fetch_url": {
        "description": "Fetch the contents of a URL.",
        "params": {"url": "URL to fetch"},
        "modifies_fs": False,
        "fn": _tool_fetch_url,
    },
    "edit_file": {
        "description": (
            "Replace `old_text` with `new_text` in `path`. The old_text must "
            "match exactly. The user will be asked to confirm."
        ),
        "params": {
            "path": "file path",
            "old_text": "exact text to replace",
            "new_text": "replacement text",
        },
        "modifies_fs": True,
        "fn": _tool_edit_file,
    },
    "create_file": {
        "description": (
            "Create a new file with the given content. Parent directories are "
            "created. The user will be asked to confirm."
        ),
        "params": {"path": "file path", "content": "full file content"},
        "modifies_fs": True,
        "fn": _tool_create_file,
    },
}


def describe_tools() -> str:
    """Markdown bullet list of available tools for the LLM."""
    lines = []
    for name, meta in TOOLS.items():
        params = ", ".join(f"{k}: {v}" for k, v in meta["params"].items())
        gate = " (asks user permission)" if meta["modifies_fs"] else ""
        lines.append(f"- `{name}({params})`{gate} — {meta['description']}")
    return "\n".join(lines)


async def run_tool(name: str, params: dict) -> str:
    """Dispatch a tool call. The caller is responsible for permission gating."""
    meta = TOOLS.get(name)
    if not meta:
        return f"Error: unknown tool '{name}'. Available: {list(TOOLS.keys())}"
    try:
        return await meta["fn"](**(params or {}))
    except TypeError as e:
        return f"Error: invalid params for {name}: {e}"
    except Exception as e:
        return f"Error running {name}: {e}"
