# brodex

> A terminal-based AI coding assistant powered by Groq's free, blazing-fast inference API.

brodex is an open, permission-driven coding agent for your terminal. Describe what you need in plain English — brodex explores your codebase, searches the web, drafts and applies code changes, and always asks before touching your files.

---

## Highlights

- **Smart exploration** — the model decides which files to read, which commands to run, and which queries to search.
- **Web-aware** — fetch documentation, search the web, and pull in external context when the local codebase isn't enough.
- **Direct code edits** — generates patches with explicit file paths and applies them after you approve.
- **Permission-based** — every command, file write, and side effect requires your confirmation.
- **Transparent** — shows the plan, the tools it intends to call, and the results before moving on.
- **Fast and free** — runs on Groq's hosted Llama / Gemma models with no credit card required.

## How it works

```
You ──▶ brodex plans ──▶ you approve ──▶ tools gather context ──▶ Groq reasons ──▶ you approve edits ──▶ files updated
```

1. You describe a task ("fix the bug in `app.py`", "explain the auth flow", "add error handling").
2. brodex proposes a plan: which files to read, which commands or web searches to run.
3. You approve (or decline) the plan; brodex collects the context.
4. The model produces an answer or a concrete patch with file paths.
5. For code changes, brodex shows each edit and asks for permission before writing to disk.

You can say "no" at any step to cancel.

## Installation

### 1. Get a free Groq API key

Sign up at [console.groq.com](https://console.groq.com) — no credit card required — and copy your key.

### 2. Install brodex

```bash
git clone <repo-url> brodex
cd brodex
pip install -e .
```

Requires **Python 3.10+**.

### 3. Configure your API key

```bash
export GROQ_API_KEY="gsk_..."
# Add the line above to ~/.zshrc or ~/.bash_profile to persist it.
```

### 4. Launch

```bash
brodex
```

## Usage

Once `brodex` is running, describe what you want in natural language.

| Intent | Example prompts |
| --- | --- |
| Understand code | `explain main.py`, `how is the project structured?`, `what does the auth module do?` |
| Find things | `find all TODO comments`, `where are database queries?`, `show me error handlers` |
| Write & fix code | `create a login function`, `fix the bug in app.py`, `add error handling to the API layer` |
| Refactor | `refactor this for performance`, `improve readability of utils.py` |
| Debug | `run the tests and tell me what's broken`, `why might this crash?` |
| Learn | `how do I implement caching?`, `search the web for TypeScript patterns` |

### Slash commands

| Command | Description |
| --- | --- |
| `/help` | Show in-app help |
| `/clear` | Clear conversation history |
| `/model <name>` | Switch the active Groq model |
| `/exit` | Quit the session |

## Models

Pick the model that fits the task with `/model <name>`:

| Model | Speed | Quality | Best for |
| --- | --- | --- | --- |
| `llama-3.3-70b-versatile` *(default)* | Medium | Excellent | General-purpose coding and reasoning |
| `llama-3.1-8b-instant` | Very fast | Good | Quick lookups and short answers |
| `gemma-2-9b-it` | Fast | Good | Lightweight tasks, fallback option |

## Free tier limits

Groq's free tier is generous enough for daily interactive use:

- 30 requests per minute
- No daily request cap
- No credit card required
- Access to all hosted models

## Tech stack

- **Python 3.10+**
- [`groq`](https://pypi.org/project/groq/) — official Groq Python SDK
- [`click`](https://click.palletsprojects.com/) — CLI framework
- [`rich`](https://rich.readthedocs.io/) — terminal rendering
- [`prompt_toolkit`](https://python-prompt-toolkit.readthedocs.io/) — interactive REPL
- [`httpx`](https://www.python-httpx.org/) — async HTTP client
- [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/) + [`lxml`](https://lxml.de/) — HTML parsing for web fetches

## Troubleshooting

**`GROQ_API_KEY not set`**
Export the key in your shell, or add it to your shell rc file:

```bash
export GROQ_API_KEY="gsk_..."
```

**No response or timeouts**
Check your network connection and verify the key at [console.groq.com](https://console.groq.com). Try a lighter model with `/model llama-3.1-8b-instant`.

**Model not found**
Run `/model` with no argument to list the currently supported models.

## FAQ

**Is it really free?** Yes — Groq's free tier covers all the listed models with no credit card.

**How fast is it?** Groq inference typically returns in 1–3 seconds, even for the 70B model.

**Does it work offline?** No. brodex needs network access to reach Groq's API and to fetch web content.

**Which model should I start with?** `llama-3.3-70b-versatile` (the default). Switch to `llama-3.1-8b-instant` for snappier short queries.

**Are my conversations stored anywhere?** Only in memory for the current session. History is cleared when you exit or run `/clear`.

## License

MIT
