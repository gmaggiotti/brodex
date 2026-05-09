from pathlib import Path


def read_file(file_path: str) -> str:
    """Read file contents and return as string."""
    try:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"Error: File not found: {file_path}"
        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        content = path.read_text()
        # Detect language from extension
        ext = path.suffix.lstrip('.')
        if ext:
            return f"```{ext}\n{content}\n```"
        return f"```\n{content}\n```"
    except Exception as e:
        return f"Error reading file: {e}"
