# brodex

**brodex** is an open-source, open-LLM coding CLI — a Claude Code–style assistant
that runs on whichever Groq-hosted model you point it at. It reads your
codebase, searches the web, drafts and edits files through an agentic
tool-call loop, and asks before it touches the filesystem.

```
› refactor agent.py to use the new tools_registry

󰋗 reading agent.py to see current structure
→ read_file(path='aicode/agent.py')
✓ (0.2s)

󰋗 proposing the refactor as an edit
EDIT `aicode/agent.py`
- from aicode.tools.code_tools import …
+ from aicode.tools_registry import TOOLS, run_tool
Apply edit_file? [y/N]: y
✓ (0.0s)
```

## Why brodex

* **Open LLMs, no lock-in.** Runs on Groq's free tier — Llama, Qwen, GPT-OSS,
  Gemma, and others — and switches model on the fly with `/model`.
* **Agentic, not scripted.** Each turn the model picks one tool and the loop
  feeds the result back, so brodex can chain reads, searches, and edits the
  way Claude Code does.
* **Permission only where it matters.** Read-only tools (`read_file`,
  `execute_command`, `search_web`, `fetch_url`) run silently. Anything that
  changes a file (`edit_file`, `create_file`) shows a preview and asks `y/N`
  with **no** as the default.
* **Live feedback.** Every thinking step shows a ticking elapsed-seconds
  timer plus the token usage Groq returned for that call.

## Install

Requires Python 3.9+ and a free Groq API key from
[console.groq.com](https://console.groq.com).

```bash
git clone https://github.com/gmaggiotti/brodex.git
cd brodex
pip install -e .
export GROQ_API_KEY=...   # add to your shell profile to persist
brodex
```

## Tools

| Tool              | Modifies FS | Notes                                                       |
| ----------------- | :---------: | ----------------------------------------------------------- |
| `read_file`       |      —      | Read the contents of a file.                                |
| `execute_command` |      —      | Run a read-only shell command (`ls`, `grep`, `git status`). |
| `search_web`      |      —      | DuckDuckGo HTML search, no API key.                         |
| `fetch_url`       |      —      | Fetch a URL and extract the main text.                      |
| `edit_file`       |     yes     | Replace exact text in a file. Asks `y/N`.                   |
| `create_file`     |     yes     | Create a new file (parents created). Asks `y/N`.            |

The model decides when to use each. The loop ends when the model replies
with prose instead of another tool call.

## REPL commands

| Command  | Effect                                |
| -------- | ------------------------------------- |
| `/help`  | Show in-app help.                     |
| `/clear` | Clear the conversation history.       |
| `/model` | Show or switch the active Groq model. |
| `/exit`  | Quit brodex.                          |

Anything else you type is sent to the agent.

## Configuration

| Variable       | Purpose                                       |
| -------------- | --------------------------------------------- |
| `GROQ_API_KEY` | **Required.** Free key from console.groq.com. |

The active model is set per-session. `/model` lists every model brodex knows
about and the per-minute token budget it assumes for each.

## Project layout

```
aicode/
├── main.py              # `brodex` entrypoint
├── repl.py              # interactive prompt + slash commands
├── intelligent_agent.py # the agentic tool-call loop
├── tools_registry.py    # tool definitions + the `modifies_fs` flag
├── tools/               # read_file, execute_command, search_web, fetch_url, edit_file
└── providers/
    └── groq_provider.py # Groq client + token-usage tracking
```

## Development

```bash
pip install -e .
python -m aicode.main      # same as `brodex`
```

Contributions welcome — the tool surface is intentionally small so it's easy
to add a new tool: define an async function, register it in
`aicode/tools_registry.py` with a `modifies_fs` flag, and the agent picks
it up automatically.

## License

MIT.
