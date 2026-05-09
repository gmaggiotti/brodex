import asyncio
import contextlib
import subprocess
import json
import re
import difflib
from pathlib import Path
from aicode.tools.code_tools import execute_command, edit_file
from aicode.tools import read_file, search_web, fetch_url


class IntelligentAgent:
    """Agent that uses LLM to decide what to explore and fetch."""

    def __init__(self, groq_provider, console=None):
        self.groq = groq_provider
        self.last_context = ""
        self.console = console

    def _print(self, text: str = ""):
        """Print with optional console object."""
        if self.console:
            self.console.print(text)
        else:
            print(text)

    def _thinking(self, message: str = "Thinking"):
        """Rolling spinner shown while the LLM is working."""
        if self.console:
            return self.console.status(
                f"[cyan]{message}…[/cyan]", spinner="dots"
            )
        return contextlib.nullcontext()

    async def ask_permission(self, what: str, details: str = "") -> bool:
        """Ask user for permission (interactive)."""
        if self.console:
            from rich.prompt import Confirm
            confirm = Confirm.ask(f"[yellow]{what}?[/yellow]", default=True)
            return confirm
        else:
            response = input(f"\n{what}? (y/n) [y]: ").lower().strip()
            return response != "n"

    async def process_user_request(self, user_message: str) -> tuple[str, str]:
        """
        Process user request with full transparency and web integration.
        """

        self._print("\n[bold cyan]󰬁 Understanding your request[/bold cyan]")
        self._print(f"[dim]{user_message}[/dim]\n")

        # Ask LLM what information it needs
        self._print("[bold cyan]󰍉 Planning exploration[/bold cyan]")

        context_request = f"""User is asking: "{user_message}"

You are a helpful coding assistant. Analyze what the user needs and gather context.

What resources do you need? Respond ONLY with JSON in this shape:
{{
    "commands": [<shell commands to discover files, e.g. "ls", "find . -name '*.py'">],
    "files_to_read": [<actual paths discovered or referenced by the user — leave empty if you don't yet know which files exist>],
    "web_searches": [<search queries, only if external info is needed>],
    "web_fetches": [<URLs to fetch, only if needed>],
    "explanation": "<one sentence on what you're investigating>"
}}

Rules:
- Do NOT include placeholder filenames like main.py or app.py unless the user named them.
- Prefer running a discovery command first; only list files_to_read once you know they exist.
- Return ONLY valid JSON, no prose.
"""

        with self._thinking("Planning exploration"):
            llm_context_request = await self.groq.send_message(context_request)
        context_data = self._extract_json(llm_context_request)

        if not context_data:
            context_data = {
                "commands": ["find . -type f \\( -name '*.py' -o -name '*.js' \\) | head -20"],
                "files_to_read": [],
                "web_searches": [],
                "web_fetches": [],
                "explanation": "Exploring codebase",
            }

        # Show plan and ask permission
        self._print("[bold yellow]󰋗 Exploration plan[/bold yellow]")
        self._print(f"[dim]{context_data.get('explanation', '')}[/dim]\n")

        if context_data.get("commands"):
            self._print("[dim]Codebase exploration:[/dim]")
            for cmd in context_data.get("commands", [])[:5]:
                self._print(f"  [dim]$[/dim] {cmd}")

        if context_data.get("files_to_read"):
            self._print("[dim]Files to read:[/dim]")
            for f in context_data.get("files_to_read", [])[:5]:
                self._print(f"  [dim]󰈙[/dim] {f}")

        if context_data.get("web_searches"):
            self._print("[dim]Web searches:[/dim]")
            for s in context_data.get("web_searches", [])[:3]:
                self._print(f"  [dim]󰎔[/dim] {s}")

        if context_data.get("web_fetches"):
            self._print("[dim]Fetch from web:[/dim]")
            for url in context_data.get("web_fetches", [])[:3]:
                self._print(f"  [dim]󰌐[/dim] {url}")

        # Read-only exploration runs without asking — only writes need permission.
        self._print("\n[bold cyan]󰃐 Gathering context[/bold cyan]\n")

        gathered_context = []
        gathered_context.append(f"**Request:** {user_message}\n")
        gathered_context.append(f"**Plan:** {context_data.get('explanation', '')}\n")
        gathered_context.append("---\n")

        # Execute commands
        for cmd in context_data.get("commands", [])[:5]:
            self._print(f"[dim]$ {cmd}[/dim]")
            try:
                output = await execute_command(cmd)
                if output and output != "(no output)":
                    gathered_context.append(f"\n**Command:** `{cmd}`\n```\n{output[:500]}\n```")
                    self._print(f"[green]✓[/green]")
            except Exception as e:
                self._print(f"[red]✗[/red]")

        # Read files — skip ones that don't exist instead of surfacing the error
        for file in context_data.get("files_to_read", [])[:5]:
            if not Path(file).is_file():
                continue
            self._print(f"[dim]󰈙 {file}[/dim]")
            content = read_file(file)
            if content and "Error" not in content:
                gathered_context.append(f"\n**File:** `{file}`\n{content}")
                self._print(f"[green]✓[/green]")
            else:
                self._print(f"[red]✗[/red]")

        # Web searches
        for query in context_data.get("web_searches", [])[:3]:
            self._print(f"[dim]󰎔 Searching: {query}[/dim]")
            try:
                results = await search_web(query)
                if results and "No search results" not in results:
                    gathered_context.append(f"\n**Web search:** `{query}`\n{results}")
                    self._print(f"[green]✓[/green]")
            except:
                self._print(f"[red]✗[/red]")

        # Fetch URLs
        for url in context_data.get("web_fetches", [])[:3]:
            self._print(f"[dim]󰌐 Fetching: {url}[/dim]")
            try:
                content = await fetch_url(url)
                if content and "Error" not in content:
                    gathered_context.append(f"\n**From web:** {content}")
                    self._print(f"[green]✓[/green]")
            except:
                self._print(f"[red]✗[/red]")

        context_str = "\n".join(gathered_context)
        self.last_context = context_str

        # Get AI response
        self._print("\n[bold cyan]󰌞 Asking AI[/bold cyan]")

        full_request = f"""{user_message}

---
## Context
{context_str}

---
Based on this context, please help."""

        with self._thinking("Thinking"):
            ai_response = await self.groq.send_message(full_request)

        return context_str, ai_response

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from response."""
        if not text:
            return None

        try:
            # Try to parse the whole response as JSON first
            return json.loads(text)
        except:
            pass

        try:
            # Look for JSON object in the text
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                json_str = match.group()
                return json.loads(json_str)
        except:
            pass

        try:
            # Try to find JSON between triple backticks
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
        except:
            pass

        return None

    async def understand_request_and_help(self, message: str) -> tuple[str, str]:
        """Main entry point for analysis requests."""
        return await self.process_user_request(message)

    async def apply_code_changes(self, user_message: str) -> tuple[str, str]:
        """Apply code changes with full permission workflow."""

        self._print("\n[bold cyan]󰘧 Code modification[/bold cyan]")
        self._print(f"[dim]{user_message}[/dim]\n")

        # Step 1: Plan what to read
        self._print("[bold cyan]󰍉 Planning analysis[/bold cyan]")

        understand_request = f"""User wants to: "{user_message}"

You are a code assistant. Plan what to read from their codebase.
Respond with ONLY this JSON structure (no other text):
{{
    "commands": [<shell commands to discover relevant files>],
    "files_to_read": [<actual paths the user named or that you've already discovered — leave empty otherwise>],
    "web_searches": [<queries, only if external info is needed>],
    "web_fetches": [],
    "explanation": "<one sentence on what you're investigating>"
}}

Rules:
- Do NOT invent placeholder filenames like main.py or app.py — only list files you know exist.
- Prefer a discovery command first; populate files_to_read only with real paths."""

        with self._thinking("Planning analysis"):
            llm_context_req = await self.groq.send_message(understand_request)
        context_data = self._extract_json(llm_context_req)

        if not context_data:
            self._print("[yellow]⚠ Could not parse analysis, using defaults[/yellow]")

        if not context_data:
            context_data = {
                "commands": ["find . -type f \\( -name '*.py' -o -name '*.js' \\) | head -20"],
                "files_to_read": [],
                "web_searches": [],
                "web_fetches": [],
                "explanation": "Exploring codebase",
            }

        # Show plan
        self._print(f"[dim]{context_data.get('explanation', '')}[/dim]\n")

        existing_files = [
            f for f in context_data.get("files_to_read", [])[:5]
            if Path(f).is_file()
        ]
        if existing_files:
            self._print("[dim]Will read:[/dim]")
            for f in existing_files:
                self._print(f"  [dim]󰈙[/dim] {f}")

        # Read-only analysis runs without asking — only the apply step prompts.
        self._print("\n[bold cyan]󰃐 Analyzing[/bold cyan]\n")

        gathered = []

        for cmd in context_data.get("commands", [])[:3]:
            self._print(f"[dim]$ {cmd}[/dim]")
            try:
                output = await execute_command(cmd)
                if output:
                    gathered.append(f"```\n{cmd}\n{output[:300]}\n```")
                    self._print(f"[green]✓[/green]")
            except:
                self._print(f"[red]✗[/red]")

        for file in existing_files:
            self._print(f"[dim]󰈙 {file}[/dim]")
            content = read_file(file)
            if content and "Error" not in content:
                gathered.append(f"**File:** `{file}`\n{content}")
                self._print(f"[green]✓[/green]")
            else:
                self._print(f"[red]✗[/red]")

        for query in context_data.get("web_searches", [])[:2]:
            self._print(f"[dim]󰎔 {query}[/dim]")
            try:
                results = await search_web(query)
                if results:
                    gathered.append(f"**Search:** {query}\n{results}")
                    self._print(f"[green]✓[/green]")
            except:
                self._print(f"[red]✗[/red]")

        context_str = "\n".join(gathered)

        # Step 2: Generate code changes
        self._print("\n[bold cyan]󰌞 Generating code[/bold cyan]")

        code_prompt = f"""User wants: {user_message}

Context:
{context_str}

---

Generate code changes. Respond with ONLY this JSON (no explanations):
{{
    "changes": [
        {{
            "action": "create",
            "file": "new_file.py",
            "content": "file content here"
        }},
        {{
            "action": "edit",
            "file": "existing.py",
            "old_text": "original code",
            "new_text": "new code"
        }}
    ],
    "explanation": "Brief explanation",
    "next_steps": "What to do next"
}}

Important:
- Return ONLY the JSON object, nothing else
- For edits, old_text must be EXACT match
- Preserve all whitespace and formatting
- For creates, include complete file content"""

        with self._thinking("Generating code"):
            llm_response = await self.groq.send_message(code_prompt)
        changes_data = self._extract_json(llm_response)

        if not changes_data or "changes" not in changes_data:
            self._print("[red]✗ Could not generate code[/red]")
            self._print(f"[dim]Response: {llm_response[:300]}[/dim]")

            # Try to extract any actionable text from the response
            if "Error" in llm_response or "error" in llm_response:
                self._print("[yellow]The AI encountered an error. Try:[/yellow]")
                self._print("[dim]  • Make sure your API key is valid[/dim]")
                self._print("[dim]  • Check your internet connection[/dim]")
                self._print("[dim]  • Try a simpler request[/dim]")

            return context_str, llm_response

        # Show planned changes
        self._print("\n[bold yellow]󰋗 Planned changes[/bold yellow]\n")

        for i, change in enumerate(changes_data.get("changes", []), 1):
            action = change.get("action")
            file_path = change.get("file")

            if action == "create":
                content = change.get("content", "")
                self._print(f"[cyan]{i}.[/cyan] [bold]CREATE[/bold] `{file_path}`")
                self._print("[dim]--- New file ---[/dim]")

                # Show code in diff format
                for line_num, line in enumerate(content.splitlines(), 1):
                    # Show line numbers and code with + prefix
                    line_str = f"{line_num:4d} | {line}"
                    self._print(f"[green]+ {line_str}[/green]")

                if len(content.splitlines()) > 20:
                    self._print(f"[dim]... ({len(content.splitlines())} lines total)[/dim]")
                self._print()

            elif action == "edit":
                old_text = change.get("old_text", "")
                new_text = change.get("new_text", "")
                self._print(f"[cyan]{i}.[/cyan] [bold]EDIT[/bold] `{file_path}`")
                self._print("[dim]--- Diff ---[/dim]")

                # Show diff
                old_lines = old_text.splitlines(keepends=True)
                new_lines = new_text.splitlines(keepends=True)

                # Ensure we have lines to diff
                if not old_lines:
                    old_lines = [old_text] if old_text else [""]
                if not new_lines:
                    new_lines = [new_text] if new_text else [""]

                diff = list(difflib.unified_diff(
                    old_lines, new_lines,
                    lineterm=""
                ))

                if diff and len(diff) > 2:
                    for line in diff[2:]:  # Skip file headers
                        if line.startswith("+") and not line.startswith("+++"):
                            self._print(f"[green]{line.rstrip()}[/green]")
                        elif line.startswith("-") and not line.startswith("---"):
                            self._print(f"[red]{line.rstrip()}[/red]")
                        else:
                            self._print(f"[dim]{line.rstrip()}[/dim]")
                else:
                    # Fallback display for simple changes
                    self._print(f"[red]- {old_text[:80].strip()}[/red]")
                    self._print(f"[green]+ {new_text[:80].strip()}[/green]")

                self._print()

        self._print(f"\n[dim]{changes_data.get('explanation', '')}[/dim]\n")

        # Ask to apply
        apply = await self.ask_permission("[yellow]󰄬 Apply changes[/yellow]")
        if not apply:
            self._print("[dim]✗ Cancelled[/dim]")
            return "", "Changes cancelled"

        # Apply changes
        self._print("\n[bold cyan]󰝤 Applying[/bold cyan]\n")

        applied = []

        for change in changes_data.get("changes", []):
            action = change.get("action")
            file_path = change.get("file")

            if action == "create":
                content = change.get("content", "")
                try:
                    path = Path(file_path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                    self._print(f"[green]✓[/green] Created `{file_path}`")
                    self._print(f"[dim]{len(content)} chars[/dim]\n")
                    applied.append(f"✓ Created `{file_path}`")
                except Exception as e:
                    self._print(f"[red]✗[/red] Failed: {e}")
                    applied.append(f"✗ Failed to create `{file_path}`")

            elif action == "edit":
                old_text = change.get("old_text", "")
                new_text = change.get("new_text", "")
                try:
                    # Show diff
                    old_lines = old_text.splitlines(keepends=True)
                    new_lines = new_text.splitlines(keepends=True)
                    diff = list(difflib.unified_diff(
                        old_lines, new_lines,
                        fromfile=f"{file_path} (old)",
                        tofile=f"{file_path} (new)",
                        lineterm=""
                    ))

                    if diff:
                        self._print(f"[green]✓[/green] Editing `{file_path}`")
                        self._print("[dim]--- Diff ---[/dim]")
                        for line in diff[2:]:  # Skip the file headers
                            if line.startswith("+"):
                                self._print(f"[green]{line.rstrip()}[/green]")
                            elif line.startswith("-"):
                                self._print(f"[red]{line.rstrip()}[/red]")
                            else:
                                self._print(f"[dim]{line.rstrip()}[/dim]")
                        self._print()

                    # Apply the change
                    result = await edit_file(file_path, old_text, new_text)
                    applied.append(f"✓ Edited `{file_path}`")
                except Exception as e:
                    self._print(f"[red]✗[/red] Failed: {e}")
                    applied.append(f"✗ Failed to edit `{file_path}`")

        # Summary
        self._print("\n[bold cyan]󰺏 Summary[/bold cyan]")
        self._print(f"\n[dim]{changes_data.get('explanation', '')}[/dim]")
        self._print(f"\n[dim]Next: {changes_data.get('next_steps', '')}[/dim]")

        summary = f"""## Changes Applied

{chr(10).join(applied)}

## What Changed
{changes_data.get('explanation', '')}

## Next Steps
{changes_data.get('next_steps', '')}"""

        return summary, summary
