# AI Terminal Agent

A lightweight, cross-platform AI coding agent that lives in your terminal. Describe a task in plain English, and it plans and executes shell commands, reads/writes files, and reports the results — with safety checks and interactive confirmation.

Works on **Linux**, **macOS**, and **Windows**. Uses any **OpenAI-compatible** chat model (OpenAI, Groq, Gemini, OpenRouter, Ollama, LM Studio, etc.).

## Features

- 🤖 **LLM-driven tool loop** — the model decides what to do, runs tools, and iterates until done
- 🛠️ **Multiple tools** — `run_command`, `read_file`, `write_file`, `edit_file`, `list_files`
- 🌍 **Cross-platform** — auto-detects OS and uses the right shell (`bash`/`sh` on Unix, `cmd`/PowerShell on Windows)
- 🛡️ **Safety layer** — flags destructive commands (Unix *and* Windows patterns) and asks for explicit confirmation
- ⚡ **Auto-approve budget** — safe commands run without prompting (configurable)
- 🎨 **Rich REPL** — colored output, slash commands (`/help`, `/clear`, `/cd`, `/exit`)
- 🔌 **Multi-provider** — built-in presets for Groq, Gemini, OpenRouter, Cerebras, SambaNova, OpenAI
- 📦 **Installable** — `pip install -e .` gives you `tell` and `aita` console commands

## Project layout

```
tell-terminal-agent/
├── ai_terminal/
│   ├── __init__.py      # public API + version
│   ├── __main__.py      # `python -m ai_terminal` entry point
│   ├── agent.py         # LLM + tool-calling loop
│   ├── cli.py           # interactive REPL + one-shot CLI
│   ├── config.py        # settings from .env / environment
│   ├── executor.py      # cross-platform subprocess runner
│   ├── safety.py        # dangerous-command detection (Unix + Windows)
│   └── tools.py         # tool JSON schemas for the LLM
├── tests/
│   ├── test_config.py
│   ├── test_executor.py
│   ├── test_safety.py
│   └── test_tools.py
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/mylab12345/tell-terminal-agent.git
cd tell-terminal-agent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Add your API key

```bash
cp .env.example .env
# Edit .env and set your preferred provider + API key
```

The easiest free option is **Groq** — get a key at https://console.groq.com/keys and set:

```
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
```

### 3. Run it

**Interactive REPL:**
```bash
tell
# or: aita
# or: python -m ai_terminal
```

**One-shot query:**
```bash
tell "find all TODO comments in this project"
tell "create a Flask hello world app"
tell "run the tests and fix any failures"
```

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `groq` | Provider preset (`groq`, `gemini`, `openrouter`, `cerebras`, `sambanova`, `openai`) |
| `GROQ_API_KEY` | — | API key for Groq |
| `GEMINI_API_KEY` | — | API key for Google Gemini |
| `OPENROUTER_API_KEY` | — | API key for OpenRouter |
| `OPENAI_API_KEY` | — | API key for OpenAI (also used as fallback for any provider) |
| `AI_MODEL` | *(per provider)* | Override the default model |
| `OPENAI_BASE_URL` | *(per provider)* | Override the base URL (for custom endpoints) |
| `AI_TEMPERATURE` | `0.2` | Sampling temperature (0.0–1.0) |
| `MAX_AUTO_STEPS` | `5` | Non-dangerous commands auto-approved per turn (`0` = always ask) |
| `COMMAND_TIMEOUT` | `120` | Max seconds per command before timeout |

### Using a local model (Ollama example)

```
AI_PROVIDER=openai
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
AI_MODEL=llama3.1
```

## Usage examples

```
agent (project)> list the largest files in this folder
agent (project)> create a python project called demo with a hello world script
agent (project)> show me the top 5 processes by memory usage
agent (project)> find all .py files containing the word TODO
agent (project)> read main.py and suggest improvements
agent (project)> run pytest and fix any failing tests
```

### Slash commands

| Command | Action |
|---|---|
| `/help` | Show help |
| `/clear` | Clear conversation history |
| `/cwd` | Print current working directory |
| `/cd PATH` | Change working directory |
| `/exit` | Quit (also Ctrl+C / Ctrl+D) |

## How it works

1. Your request is sent to the LLM with a system prompt describing the environment and available tools.
2. The model returns one or more tool calls (commands, file operations).
3. Each command is checked by the safety layer:
   - **Dangerous** → always asks for `y/N` confirmation
   - **Safe** → auto-approved up to `MAX_AUTO_STEPS`, then asks
4. The tool runs and the result is fed back to the model.
5. The loop continues until the model stops calling tools and returns a final answer.

## Tools

| Tool | Description |
|---|---|
| `run_command` | Execute a shell command (auto-detects platform shell) |
| `read_file` | Read a file's contents (with size limit) |
| `write_file` | Create or overwrite a file (auto-creates parent dirs) |
| `edit_file` | Search-and-replace within a file |
| `list_files` | List directory contents (optionally recursive) |

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Safety

This agent runs real commands on your real machine. It is **not** sandboxed. Mitigations:

- A denylist of destructive patterns (Unix + Windows) triggers confirmation prompts
- A per-turn auto-approve budget prevents runaway execution
- File operations and commands are always shown before execution
- A configurable timeout kills long-running commands

**You are responsible for reviewing actions before approving them.** Never give an AI agent access to a machine with data you cannot afford to lose.

## License

MIT
