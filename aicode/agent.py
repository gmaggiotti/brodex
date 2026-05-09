import asyncio
import re
from aicode.tools.code_tools import (
    execute_command,
    list_files,
    tree_view,
    git_status,
    git_diff,
    run_file,
    find_files,
    grep_search,
)
from aicode.tools import read_file, search_web, fetch_url


class Agent:
    """Intelligent agent that understands developer requests and executes appropriate tools."""

    async def process_request(self, message: str) -> dict:
        """
        Parse developer request and execute appropriate tools.
        Returns: {
            'tools_used': [list of tools],
            'results': {tool_name: output},
            'context': formatted context to send to AI
        }
        """
        results = {}
        context_parts = []
        tools_used = []

        message_lower = message.lower()

        # Detect file reading requests
        if self._matches(message_lower, ["show", "read", "view", "open", "display", "@"]):
            file_results = await self._extract_and_read_files(message)
            if file_results:
                results["files"] = file_results
                tools_used.append("file_read")
                context_parts.append(f"## Files Read\n{file_results}")

        # Detect code search requests
        if self._matches(
            message_lower,
            ["find", "search", "grep", "where", "locate", "look for", "all", "get all", "show me all"],
        ):
            search_results = await self._search_code(message)
            if search_results:
                results["search"] = search_results
                tools_used.append("grep")
                context_parts.append(f"## Search Results\n{search_results}")

        # Detect project structure requests
        if self._matches(message_lower, ["structure", "tree", "layout", "what's in", "explore"]):
            tree_results = await tree_view(".", depth=3)
            results["tree"] = tree_results
            tools_used.append("tree")
            context_parts.append(f"## Project Structure\n```\n{tree_results}\n```")

        # Detect test/build requests
        if self._matches(
            message_lower,
            ["test", "run", "build", "execute", "compile", "check", "verify"],
        ):
            cmd_results = await self._execute_relevant_commands(message)
            if cmd_results:
                results["execution"] = cmd_results
                tools_used.append("exec")
                for cmd, output in cmd_results.items():
                    context_parts.append(f"## Command: {cmd}\n```\n{output}\n```")

        # Detect git requests
        if self._matches(message_lower, ["git", "commit", "diff", "status", "change"]):
            git_results = await self._get_git_info(message)
            if git_results:
                results["git"] = git_results
                tools_used.append("git")
                context_parts.append(f"## Git Info\n```\n{git_results}\n```")

        # Detect web search requests
        if self._matches(
            message_lower,
            ["search the web", "lookup", "research", "find on web", "google"],
        ):
            search_results = await search_web(message)
            if search_results and "No search results" not in search_results:
                results["web_search"] = search_results
                tools_used.append("web_search")
                context_parts.append(search_results)

        # Detect URL fetch requests
        urls = re.findall(r"https?://[^\s]+", message)
        if urls:
            for url in urls:
                fetch_results = await fetch_url(url)
                results[f"fetch_{url[:30]}"] = fetch_results
                tools_used.append("fetch")
                context_parts.append(fetch_results)

        return {
            "tools_used": tools_used,
            "results": results,
            "context": "\n\n".join(context_parts),
        }

    def _matches(self, text: str, keywords: list) -> bool:
        """Check if text contains any of the keywords."""
        return any(keyword in text for keyword in keywords)

    async def _extract_and_read_files(self, message: str) -> str:
        """Extract file references and read them."""
        # Look for @file patterns or explicit file mentions
        file_pattern = r"@?([\w\./\-]+\.[\w]+)"
        matches = re.findall(file_pattern, message)

        results = []
        for file_path in matches[:5]:  # Limit to 5 files
            content = read_file(file_path)
            if "Error" not in content:
                results.append(content)

        return "\n\n".join(results) if results else ""

    async def _search_code(self, message: str) -> str:
        """Search for code patterns."""
        # Extract search terms
        terms = re.findall(
            r"(?:find|search|grep|look for|all|show me all)\s+(?:all\s+)?['\"]?([^'\"?\n]+)['\"]?",
            message,
        )
        if not terms:
            # Try to extract quoted text
            terms = re.findall(r"['\"]([^'\"]+)['\"]", message)

        # If still no terms, try common patterns
        if not terms:
            if "function" in message.lower():
                terms = ["def ", "function "]
            elif "todo" in message.lower() or "fixme" in message.lower():
                terms = ["TODO", "FIXME"]
            elif "error" in message.lower():
                terms = ["error", "Error", "Exception"]
            elif "import" in message.lower():
                terms = ["import ", "from "]

        results = []
        for term in terms[:5]:  # Limit to 5 searches
            term = term.strip()
            if term and len(term) > 1:
                search_result = await grep_search(term)
                if search_result and "No matches" not in search_result:
                    results.append(search_result)

        return "\n\n".join(results) if results else ""

    async def _execute_relevant_commands(self, message: str) -> dict:
        """Detect and execute relevant commands."""
        results = {}
        message_lower = message.lower()

        # Test commands
        if any(word in message_lower for word in ["test", "pytest", "jest", "vitest"]):
            if "pytest" in message_lower or "python" in message_lower:
                output = await execute_command("python -m pytest -v --tb=short 2>&1 | head -50")
                results["pytest"] = output
            elif "npm" in message_lower or "jest" in message_lower or "node" in message_lower:
                output = await execute_command("npm test 2>&1 | head -50")
                results["npm_test"] = output

        # Build commands
        if "build" in message_lower:
            if "npm" in message_lower:
                output = await execute_command("npm run build 2>&1 | head -50")
                results["npm_build"] = output
            elif "python" in message_lower:
                output = await execute_command("python setup.py build 2>&1 | head -50")
                results["python_build"] = output

        # Run file if mentioned
        file_match = re.search(r"run\s+([^\s]+\.(py|js|ts|go|sh|rb))", message_lower)
        if file_match:
            file_path = file_match.group(1)
            output = await run_file(file_path)
            results[f"run_{file_path}"] = output

        # Default: show git status and project structure
        if not results:
            status = await git_status()
            results["git_status"] = status

        return results

    async def _get_git_info(self, message: str) -> str:
        """Get relevant git information."""
        message_lower = message.lower()

        if "diff" in message_lower:
            return await git_diff()
        else:
            return await git_status()

    async def understand_and_help(
        self, message: str, groq_provider
    ) -> tuple[str, str]:
        """
        Understand developer request, gather context, and get AI help.
        Returns: (gathered_context, ai_response)
        """
        # Process request and gather context
        agent_result = await self.process_request(message)

        # If we gathered context, prepend it to the message
        if agent_result["context"]:
            full_message = f"{message}\n\n---\nContext:\n{agent_result['context']}"
        else:
            full_message = message

        # Get AI response
        ai_response = await groq_provider.send_message(full_message)

        return agent_result["context"], ai_response
