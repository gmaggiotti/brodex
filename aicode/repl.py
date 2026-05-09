import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from aicode.providers.groq_provider import GroqProvider
from aicode.intelligent_agent import IntelligentAgent


SLASH_COMMANDS = [
    ("/help", "Show help"),
    ("/clear", "Clear history"),
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
  /help       Show this help
  /clear      Clear history
  /model      Show or switch AI model
  /exit       Exit brodex

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

    def _is_code_request(self, message: str) -> bool:
        """Detect if user is asking to write/fix code."""
        keywords = [
            "write", "create", "fix", "implement", "build", "generate",
            "add", "refactor", "optimize", "improve", "debug", "patch",
            "modify", "change", "update", "convert", "rewrite", "code"
        ]
        return any(kw in message.lower() for kw in keywords)

    async def handle_special_command(self, message: str) -> str | None:
        """Handle slash commands. Returns 'exit', 'handled', or None."""
        if message.startswith("/exit"):
            return "exit"
        elif message.startswith("/clear"):
            self.provider.clear_history()
            self.console.print("[dim]✓ Cleared history[/dim]")
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

    async def process_request(self, user_message: str):
        """Process request using intelligent agent."""
        is_code_request = self._is_code_request(user_message)

        # Process request - agent will show all progress
        if is_code_request:
            summary, response = await self.agent.apply_code_changes(user_message)
        else:
            summary, response = await self.agent.understand_request_and_help(user_message)

        # Show final response for analysis
        if not is_code_request and response and response != "Cancelled":
            self.console.print("\n[bold green]󰌞 Response[/bold green]")
            self.console.print(response)

        return summary, response

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

                    # Process request
                    await self.process_request(user_input)
                    self.console.print()

                except KeyboardInterrupt:
                    self.console.print()
                    continue
                except EOFError:
                    break
        finally:
            self.console.print("\n[dim]Goodbye![/dim]")
