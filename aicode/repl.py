import asyncio
import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from aicode import mcp_config
from aicode.providers.groq_provider import GroqProvider
from aicode.intelligent_agent import IntelligentAgent


SLASH_COMMANDS = [
    ("/help", "Show help"),
    ("/clear", "Clear history"),
    ("/compact", "Summarize history into a compact context"),
    ("/rewind", "Undo the last user turn(s)"),
    ("/mcp", "Add and manage MCP servers"),
    ("/model", "Show or switch AI model"),
    ("/exit", "Exit brodex"),
]


class SlashCommandCompleter(Completer):
    """Completer that shows slash commands when the line starts with '/'."""

    def __init__(self, commands):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        for name, description in self.commands:
            if name.startswith(text):
                yield Completion(
                    name,
                    start_position=-len(text),
                    display=name,
                    display_meta=description,
                )


class REPL:
    def __init__(self):
        self.console = Console()
        self.history = InMemoryHistory()
        self.session = PromptSession(
            history=self.history,
            completer=SlashCommandCompleter(SLASH_COMMANDS),
            complete_while_typing=True,
        )
        self.provider = None
        self.agent = None
        self.history_snapshots: list[list[dict]] = []

    async def start(self):
        """Initialize Groq provider."""
        self.console.print("[bold cyan]󰬁 Initializing brodex[/bold cyan]")
        try:
            self.provider = GroqProvider()
            self.agent = IntelligentAgent(self.provider, console=self.console)
            self.console.print("[bold green]✓ Ready[/bold green]")
        except ValueError as e:
            self.console.print(f"[bold red]✗ Error: {e}[/bold red]")
            raise

    def show_welcome(self):
        """Show welcome screen."""
        welcome = """[bold cyan]brodex[/bold cyan] — AI coding assistant powered by [cyan]Groq[/cyan]

Describe what you need. brodex will:
• Explore your codebase
• Search the web for information
• Write and fix code
• Always ask permission before action

[dim]Type /help for commands or just start describing what you need[/dim]"""

        self.console.print(Panel(welcome, border_style="cyan", padding=(1, 2)))

    def show_help(self):
        """Show help message."""
        help_text = """
[bold cyan]Commands[/bold cyan]
  /help              Show this help
  /clear             Clear history
  /compact           Summarize history into a compact context block
  /rewind [n]        Undo the last n user turns (default 1)
  /mcp               List configured MCP servers
  /mcp add <name> <command> [args...]   Register an MCP server
  /mcp remove <name>                    Drop an MCP server
  /model             Show or switch AI model
  /exit              Exit brodex

[bold cyan]Input[/bold cyan]
  Type your request and press Enter
  Paste code, errors, or multi-line text directly

[bold cyan]Examples[/bold cyan]

Understand code:
  "explain main.py"
  "what does this function do?"
  "show me all errors"

Find things:
  "find all TODO comments"
  "where are database queries?"
  "show project structure"

Write code:
  "create a login function"
  "fix the bug in app.py"
  "refactor for performance"
  "add error handling"

Learn:
  "how do I use async/await?"
  "search for python best practices"
  "explain how this works"

Paste & Ask:
  Paste error messages, code, or logs
  › I got this error:
    TypeError: cannot unpack...

  Then ask brodex to help fix it

[bold cyan]Features[/bold cyan]
  • Natural language requests
  • Multiline input (paste code/errors)
  • Web search and fetch
  • File reading and writing
  • Command execution
  • Always asks permission
  • Shows diffs when changing files

Just describe what you need. No special syntax required!
"""
        self.console.print(Markdown(help_text))

    async def handle_special_command(self, message: str) -> str | None:
        """Handle slash commands. Returns 'exit', 'handled', or None."""
        if message.startswith("/exit"):
            return "exit"
        elif message.startswith("/clear"):
            self.provider.clear_history()
            self.history_snapshots.clear()
            self.console.print("[dim]✓ Cleared history[/dim]")
            return "handled"
        elif message.startswith("/compact"):
            await self._handle_compact()
            return "handled"
        elif message.startswith("/rewind"):
            self._handle_rewind(message)
            return "handled"
        elif message.startswith("/mcp"):
            self._handle_mcp(message)
            return "handled"
        elif message.startswith("/model"):
            parts = message.split(maxsplit=1)
            models = self.provider.get_models()
            if len(parts) > 1:
                choice = parts[1].strip()
                model = None
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        model = models[idx]
                elif choice in models:
                    model = choice
                if model is None:
                    self.console.print(f"[red]Unknown model: {choice}[/red]")
                    self.console.print(f"[dim]Available: {', '.join(models)}[/dim]")
                else:
                    self.provider.model = model
                    self.console.print(f"[dim]Model: {model}[/dim]")
            else:
                self.console.print(f"[dim]Current model: {self.provider.model}[/dim]")
                self.console.print("[dim]Available models:[/dim]")
                for i, name in enumerate(models, 1):
                    marker = "•" if name == self.provider.model else " "
                    self.console.print(f"  [dim]{marker} {i:>2}. {name}[/dim]")
                self.console.print("[dim]Switch with: /model <name|number>[/dim]")
            return "handled"
        elif message.startswith("/help"):
            self.show_help()
            return "handled"
        return None

    async def _handle_compact(self):
        if not self.provider.messages:
            self.console.print("[dim]Nothing to compact[/dim]")
            return
        before = len(self.provider.messages)
        self.console.print("[dim]󰗋 Compacting history…[/dim]")
        summary = await self.provider.compact_history()
        if not summary:
            self.console.print("[red]✗ Compact failed[/red]")
            return
        # `/rewind` after a compact would un-compact, which is desirable, so
        # we leave snapshots intact.
        after = len(self.provider.messages)
        self.console.print(
            f"[dim]✓ Compacted {before} messages → {after}[/dim]"
        )
        self.console.print(Panel(summary, title="Compacted context", border_style="cyan"))

    def _handle_rewind(self, message: str):
        parts = message.split(maxsplit=1)
        n = 1
        if len(parts) > 1:
            try:
                n = max(1, int(parts[1].strip()))
            except ValueError:
                self.console.print(f"[red]Invalid count: {parts[1]!r}[/red]")
                return
        if not self.history_snapshots:
            self.console.print("[dim]Nothing to rewind[/dim]")
            return
        n = min(n, len(self.history_snapshots))
        snapshot = None
        for _ in range(n):
            snapshot = self.history_snapshots.pop()
        self.provider.messages = [m.copy() for m in snapshot]
        self.console.print(
            f"[dim]✓ Rewound {n} turn{'s' if n != 1 else ''} "
            f"({len(self.provider.messages)} message{'s' if len(self.provider.messages) != 1 else ''} now)[/dim]"
        )

    def _handle_mcp(self, message: str):
        try:
            tokens = shlex.split(message)
        except ValueError as e:
            self.console.print(f"[red]Could not parse: {e}[/red]")
            return
        sub = tokens[1] if len(tokens) > 1 else "list"

        if sub == "list":
            servers = mcp_config.list_servers()
            if not servers:
                self.console.print(
                    f"[dim]No MCP servers configured. "
                    f"Add one with `/mcp add <name> <command> [args...]`.[/dim]"
                )
                self.console.print(f"[dim]Config: {mcp_config.config_path()}[/dim]")
                return
            for name, spec in servers.items():
                cmd_line = " ".join([spec["command"], *spec.get("args", [])])
                env = spec.get("env") or {}
                env_str = (" env=" + ",".join(f"{k}={v}" for k, v in env.items())) if env else ""
                self.console.print(f"  [cyan]{name}[/cyan]  [dim]{cmd_line}{env_str}[/dim]")
            self.console.print(f"[dim]Config: {mcp_config.config_path()}[/dim]")
            return

        if sub == "add":
            if len(tokens) < 4:
                self.console.print(
                    "[red]Usage: /mcp add <name> <command> [args...][/red]"
                )
                return
            name = tokens[2]
            command = tokens[3]
            args = tokens[4:]
            try:
                spec = mcp_config.add_server(name, command, args)
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")
                return
            cmd_line = " ".join([spec["command"], *spec["args"]])
            self.console.print(f"[green]✓[/green] Added MCP server [cyan]{name}[/cyan]: [dim]{cmd_line}[/dim]")
            return

        if sub == "remove":
            if len(tokens) != 3:
                self.console.print("[red]Usage: /mcp remove <name>[/red]")
                return
            name = tokens[2]
            if mcp_config.remove_server(name):
                self.console.print(f"[green]✓[/green] Removed [cyan]{name}[/cyan]")
            else:
                self.console.print(f"[yellow]No such MCP server: {name}[/yellow]")
            return

        self.console.print(
            f"[red]Unknown /mcp subcommand: {sub}[/red] "
            f"[dim](use list, add, or remove)[/dim]"
        )

    async def process_request(self, user_message: str):
        """Process request using the agentic tool-call loop."""
        response = await self.agent.agentic_loop(user_message)
        return response, response

    async def run(self):
        """Run the REPL loop."""
        await self.start()
        self.show_welcome()

        try:
            while True:
                try:
                    # Get input - supports multiline
                    # Use Escape+Enter for newline, Enter alone to submit
                    user_input = await self.session.prompt_async(
                        HTML("<ansi><b><cyan>›</cyan></b></ansi> "),
                        multiline=False,
                    )

                    if not user_input.strip():
                        continue

                    # Handle special commands
                    result = await self.handle_special_command(user_input)
                    if result == "exit":
                        break
                    if result == "handled":
                        continue

                    # Snapshot history so `/rewind` can restore the
                    # state from before this turn.
                    self.history_snapshots.append(
                        [m.copy() for m in self.provider.messages]
                    )
                    await self.process_request(user_input)
                    self.console.print()

                except (KeyboardInterrupt, EOFError):
                    break
        finally:
            self.console.print("\n[dim]Goodbye![/dim]")
