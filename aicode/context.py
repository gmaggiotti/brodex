import re
from typing import List, Dict, Tuple
from aicode.tools import read_file, search_web, fetch_url


class Context:
    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.injected_content = ""

    def add_message(self, role: str, content: str):
        """Add message to history."""
        self.history.append({"role": role, "content": content})

    def clear(self):
        """Clear conversation history."""
        self.history = []
        self.injected_content = ""

    async def process_message(self, message: str) -> Tuple[str, str]:
        """
        Process message for tools and return (processed_message, injected_content).
        Handles:
        - @file/path.py → read file
        - /search query → search web
        - /fetch https://... → fetch URL
        """
        injected = []
        processed = message

        # Handle @file references
        file_pattern = r"@([\w\./\-]+)"
        for match in re.finditer(file_pattern, message):
            file_path = match.group(1)
            content = read_file(file_path)
            injected.append(content)
            processed = processed.replace(match.group(0), "")

        # Handle /search commands
        search_pattern = r"/search\s+(.+?)(?=\n|$)"
        for match in re.finditer(search_pattern, message):
            query = match.group(1)
            content = await search_web(query)
            injected.append(content)
            processed = processed.replace(match.group(0), "")

        # Handle /fetch commands
        fetch_pattern = r"/fetch\s+(https?://[\w\./\-?=&%]+)"
        for match in re.finditer(fetch_pattern, message):
            url = match.group(1)
            content = await fetch_url(url)
            injected.append(content)
            processed = processed.replace(match.group(0), "")

        injected_text = "\n\n".join(injected)
        self.injected_content = injected_text

        # Append injected content to processed message
        if injected_text:
            processed = f"{processed}\n\n---\nContext:\n{injected_text}"

        return processed, injected_text

    def get_history(self) -> str:
        """Format conversation history for display."""
        lines = []
        for msg in self.history[-10:]:  # Last 10 messages
            role = "You" if msg["role"] == "user" else "AI"
            lines.append(f"{role}: {msg['content'][:200]}")
        return "\n".join(lines) if lines else "No history"
