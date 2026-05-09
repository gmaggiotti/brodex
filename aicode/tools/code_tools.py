import subprocess
import os
from pathlib import Path
from typing import Tuple


async def execute_command(command: str) -> str:
    """Execute shell command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd(),
        )
        output = result.stdout + result.stderr
        return output[:2000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out (30s limit)"
    except Exception as e:
        return f"Error: {e}"


async def list_files(pattern: str = ".") -> str:
    """List files in project."""
    try:
        path = Path(pattern).expanduser()
        if not path.exists():
            return f"Path not found: {pattern}"

        if path.is_file():
            return f"{path}"

        files = []
        for item in sorted(path.iterdir())[:50]:  # Limit to 50 items
            if item.name.startswith("."):
                continue
            prefix = "📁" if item.is_dir() else "📄"
            files.append(f"{prefix} {item.name}")

        return "\n".join(files) if files else "No files found"
    except Exception as e:
        return f"Error: {e}"


async def tree_view(path: str = ".", depth: int = 3) -> str:
    """Show directory tree."""
    try:
        base_path = Path(path).expanduser()
        if not base_path.exists():
            return f"Path not found: {path}"

        lines = []

        def walk(p: Path, prefix: str = "", d: int = 0):
            if d > depth:
                return
            try:
                items = sorted(p.iterdir())
                for i, item in enumerate(items[:20]):  # Limit items
                    if item.name.startswith("."):
                        continue
                    is_last = i == len(items) - 1
                    current = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{current}{item.name}")
                    if item.is_dir():
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        walk(item, next_prefix, d + 1)
            except PermissionError:
                pass

        lines.insert(0, str(base_path))
        walk(base_path)
        return "\n".join(lines[:100])
    except Exception as e:
        return f"Error: {e}"


async def git_status() -> str:
    """Show git status."""
    try:
        result = subprocess.run(
            "git status --short",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return "Not a git repository"
        return result.stdout[:1000] if result.stdout else "Clean"
    except Exception as e:
        return f"Error: {e}"


async def git_diff(file: str = "") -> str:
    """Show git diff."""
    try:
        cmd = f"git diff {file}" if file else "git diff"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout[:1500] if result.stdout else "No changes"
    except Exception as e:
        return f"Error: {e}"


async def run_file(file_path: str) -> str:
    """Execute a code file."""
    try:
        path = Path(file_path).expanduser()
        if not path.exists():
            return f"File not found: {file_path}"

        ext = path.suffix.lower()

        if ext == ".py":
            cmd = f"python {file_path}"
        elif ext in [".js", ".mjs"]:
            cmd = f"node {file_path}"
        elif ext == ".ts":
            cmd = f"npx ts-node {file_path}"
        elif ext == ".sh":
            cmd = f"bash {file_path}"
        elif ext == ".go":
            cmd = f"go run {file_path}"
        elif ext == ".rb":
            cmd = f"ruby {file_path}"
        else:
            return f"Unsupported file type: {ext}"

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        return output[:2000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Execution timed out"
    except Exception as e:
        return f"Error: {e}"


async def find_files(pattern: str) -> str:
    """Search for files by name."""
    try:
        result = subprocess.run(
            f"find . -name '*{pattern}*' -type f | head -20",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        files = result.stdout.strip().split("\n")
        files = [f for f in files if f]
        return "\n".join(files) if files else f"No files matching '{pattern}'"
    except Exception as e:
        return f"Error: {e}"


async def grep_search(pattern: str, file_pattern: str = "") -> str:
    """Search for text in files."""
    try:
        cmd = f"grep -r '{pattern}' {file_pattern if file_pattern else '.'} | head -20"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout[:1500] if result.stdout else f"No matches for '{pattern}'"
    except Exception as e:
        return f"Error: {e}"


async def edit_file(file_path: str, old_text: str, new_text: str) -> str:
    """Edit a file by replacing text."""
    try:
        path = Path(file_path).expanduser()
        if not path.exists():
            return f"File not found: {file_path}"

        content = path.read_text()
        if old_text not in content:
            return f"Text not found in {file_path}"

        new_content = content.replace(old_text, new_text)
        path.write_text(new_content)
        return f"✓ File edited: {file_path}"
    except Exception as e:
        return f"Error: {e}"
