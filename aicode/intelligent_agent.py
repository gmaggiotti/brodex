import asyncio
import contextlib
import json
import re
import time
from pathlib import Path

from aicode.tools_registry import TOOLS, describe_tools, run_tool


SYSTEM_PROMPT = """You are an autonomous coding assistant running an agentic tool-call loop.

Each turn you have two options:
(a) Call exactly one tool by replying with a single JSON object and nothing else:
    {{"thought": "<one-sentence plan for this step>", "tool": "<tool name>", "params": {{...}}}}
(b) Stop and answer the user. Reply in plain prose (no JSON). The loop ends when
    your reply is not a tool-call JSON object.

Available tools:
{tools}

Guidelines:
- Read-only tools (read_file, execute_command for ls/grep/find/git, search_web, fetch_url)
  run immediately — use them freely to gather context.
- Filesystem-modifying tools (edit_file, create_file) prompt the user for confirmation.
  If the user denies, try a different approach or stop and explain.
- Use `execute_command` only for read-only/discovery commands. Never use it to modify
  files — use `edit_file` or `create_file` so the user can review and approve.
- When you have enough information, stop calling tools and reply with the final answer.
- Always emit valid JSON when calling a tool. Do not wrap it in code fences.
"""


class IntelligentAgent:
    """Agent that runs an LLM-driven tool-call loop until the LLM stops calling tools."""

    MAX_ITERATIONS = 15
    TOOL_RESULT_TRUNCATE = 1500

    def __init__(self, groq_provider, console=None):
        self.groq = groq_provider
        self.console = console
        self.last_context = ""

    def _print(self, text: str = ""):
        if self.console:
            self.console.print(text)
        else:
            print(text)

    @contextlib.asynccontextmanager
    async def _timer(self, label: str):
        """
        Live elapsed-time spinner. Yields a callable that returns elapsed
        seconds; read it after the block to record the final duration.
        """
        start = time.monotonic()

        def elapsed() -> float:
            return time.monotonic() - start

        if not self.console:
            print(f"{label}…", flush=True)
            try:
                yield elapsed
            finally:
                pass
            return

        status = self.console.status(
            f"[dim]{label}… 0.0s[/dim]", spinner="dots", spinner_style="dim"
        )
        status.__enter__()
        stop = asyncio.Event()

        async def tick():
            while not stop.is_set():
                with contextlib.suppress(Exception):
                    status.update(f"[dim]{label}… {elapsed():.1f}s[/dim]")
                try:
                    await asyncio.wait_for(stop.wait(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

        task = asyncio.create_task(tick())
        try:
            yield elapsed
        finally:
            stop.set()
            with contextlib.suppress(Exception):
                await task
            with contextlib.suppress(Exception):
                status.__exit__(None, None, None)

    def _format_usage(self) -> str:
        """Format the most recent LLM usage as a short suffix string."""
        usage = getattr(self.groq, "last_usage", None)
        if not usage:
            return ""
        return (
            f" · {usage['total_tokens']} tok "
            f"(in {usage['prompt_tokens']}, out {usage['completion_tokens']})"
        )

    async def ask_permission(self, what: str) -> bool:
        """Explicit y/n prompt. Default is NO — only an affirmative `y` proceeds."""
        if self.console:
            from rich.prompt import Confirm

            return Confirm.ask(f"[yellow]{what}?[/yellow]", default=False)
        response = input(f"\n{what}? (y/N): ").strip().lower()
        return response in ("y", "yes")

    async def agentic_loop(self, user_message: str) -> str:
        """Run the tool-call loop. Returns the final assistant message."""
        self._print(f"\n[bold cyan]󰬁 {user_message}[/bold cyan]\n")

        first_prompt = (
            SYSTEM_PROMPT.format(tools=describe_tools())
            + f"\n\nUser request: {user_message}\n\n"
            "Reply with one tool-call JSON object, or with your final answer in prose."
        )

        transcript_for_context = []
        next_message = first_prompt

        for step in range(1, self.MAX_ITERATIONS + 1):
            async with self._timer(f"Thinking (step {step})") as elapsed:
                llm_response = await self.groq.send_message(next_message)
            self._print(
                f"[dim]󰔚 step {step}: {elapsed():.1f}s{self._format_usage()}[/dim]"
            )

            action = self._extract_tool_call(llm_response)
            if action is None:
                self._print("\n[bold green]󰌞 Response[/bold green]")
                self._print(self._render_response(llm_response))
                self.last_context = "\n\n".join(transcript_for_context)
                return llm_response

            tool = action.get("tool")
            params = action.get("params") or {}
            thought = action.get("thought", "")

            if thought:
                self._print(f"[dim]󰋗 {thought}[/dim]")

            meta = TOOLS.get(tool)
            if meta is None:
                msg = (
                    f"Tool '{tool}' is not available. "
                    f"Choose one of: {list(TOOLS.keys())}."
                )
                self._print(f"[red]✗ {msg}[/red]")
                next_message = msg
                continue

            if meta["modifies_fs"]:
                self._print(self._preview_fs_change(tool, params))
                approved = await self.ask_permission(f"Apply {tool}")
                if not approved:
                    self._print("[dim]✗ Denied[/dim]")
                    next_message = (
                        f"User denied {tool}. Try a different approach, "
                        "or stop and explain."
                    )
                    continue

            self._print(f"[dim]→ {tool}({self._summarize_params(params)})[/dim]")
            async with self._timer(f"Running {tool}") as tool_elapsed:
                result = await run_tool(tool, params)
            truncated = self._truncate(result)
            self._print(f"[green]✓[/green] [dim]({tool_elapsed():.1f}s)[/dim]")

            transcript_for_context.append(f"{tool}({params}) -> {truncated}")
            next_message = (
                f"Tool `{tool}` returned:\n{truncated}\n\n"
                "Reply with the next tool-call JSON, or your final answer in prose."
            )

        self._print("[yellow]⚠ Max iterations reached without a final answer[/yellow]")
        self.last_context = "\n\n".join(transcript_for_context)
        return "Stopped after max iterations."

    def _preview_fs_change(self, tool: str, params: dict) -> str:
        path = params.get("path") or ""
        if tool == "create_file":
            new_content = params.get("content", "") or ""
            existing = ""
            label = "CREATE"
            try:
                p = Path(path).expanduser()
                if p.exists():
                    existing = p.read_text()
                    label = "OVERWRITE"
            except (OSError, UnicodeDecodeError):
                label = "OVERWRITE"
            head = f"\n[bold yellow]{label}[/bold yellow] `{path}`"
            body = self._render_edit_diff(existing, new_content)
            return f"{head}\n{body}"
        if tool == "edit_file":
            head = f"\n[bold yellow]EDIT[/bold yellow] `{path}`"
            body = self._render_edit_diff(
                params.get("old_text", "") or "",
                params.get("new_text", "") or "",
            )
            return f"{head}\n{body}"
        return f"\n[bold yellow]{tool.upper()}[/bold yellow] {params}"

    @staticmethod
    def _render_edit_diff(old: str, new: str) -> str:
        """Render a full line-diff: `-` light red for removals, `+` light green for additions."""
        import difflib

        from rich.markup import escape

        old_lines = old.splitlines()
        new_lines = new.splitlines()

        sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
        rendered = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for line in old_lines[i1:i2]:
                    rendered.append(f"[dim]  {escape(line)}[/dim]")
                continue
            if tag in ("delete", "replace"):
                for line in old_lines[i1:i2]:
                    rendered.append(f"[bright_red]- {escape(line)}[/bright_red]")
            if tag in ("insert", "replace"):
                for line in new_lines[j1:j2]:
                    rendered.append(f"[bright_green]+ {escape(line)}[/bright_green]")
        return "\n".join(rendered)

    @staticmethod
    def _render_response(text: str) -> str:
        """Dim reasoning-model `<think>…</think>` blocks so they recede vs. the answer."""
        from rich.markup import escape

        def wrap(m: re.Match) -> str:
            return f"[dim]<think>{escape(m.group(1))}</think>[/dim]"

        return re.sub(r"<think>([\s\S]*?)</think>", wrap, text)

    @staticmethod
    def _summarize_params(params: dict) -> str:
        parts = []
        for k, v in (params or {}).items():
            s = str(v).replace("\n", " ")
            if len(s) > 60:
                s = s[:60] + "…"
            parts.append(f"{k}={s!r}")
        return ", ".join(parts)

    @classmethod
    def _truncate(cls, text: str) -> str:
        if not text:
            return ""
        if len(text) <= cls.TOOL_RESULT_TRUNCATE:
            return text
        return text[: cls.TOOL_RESULT_TRUNCATE] + "…"

    def _extract_tool_call(self, text: str) -> dict | None:
        """Return a dict if `text` parses as a tool-call JSON object, else None."""
        if not text:
            return None
        candidates = [text.strip()]
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence:
            candidates.append(fence.group(1).strip())
        obj = re.search(r"\{[\s\S]*\}", text)
        if obj:
            candidates.append(obj.group())

        for cand in candidates:
            try:
                parsed = json.loads(cand)
            except Exception:
                continue
            if isinstance(parsed, dict) and "tool" in parsed:
                return parsed
        return None

    async def understand_request_and_help(self, message: str) -> tuple[str, str]:
        """Backward-compatible entry point — runs the agentic loop."""
        response = await self.agentic_loop(message)
        return self.last_context, response

    async def apply_code_changes(self, message: str) -> tuple[str, str]:
        """Backward-compatible entry point — runs the agentic loop."""
        response = await self.agentic_loop(message)
        return self.last_context, response
