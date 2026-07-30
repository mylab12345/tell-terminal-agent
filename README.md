# AITA — AI Terminal Agent for Windows 11

AITA is a small, dependency-light AI agent that lives in your terminal. You describe a task in plain English, and it plans and runs shell commands on your Windows machine to get it done — showing you each command, asking for confirmation on risky ones, and reporting the results.

It uses any **OpenAI-compatible** chat model (OpenAI, Azure OpenAI, OpenRouter, LM Studio, Ollama, etc.) and executes commands via `cmd.exe` or `powershell.exe`.

## Features

- 🤖 LLM-driven planning + command execution loop (tool/function calling)
- 🪟 Windows-first: `cmd.exe` by default, PowerShell when needed
- 🛡️ Safety layer that flags destructive commands (`format`, `del /s`, `reg add`, `shutdown`, …) and asks for explicit confirmation
- ⚡ Auto-approve budget (`MAX_AUTO_STEPS`) so safe read-only commands run without nagging
- 🎨 Rich, colored REPL with slash commands (`/help`, `/clear`, `/cd`, `/exit`)
- 🔌 Works with local models via `OPENAI_BASE_URL` (e.g. Ollama, LM Studio)
- 📦 Installable as a console script (`aita`) or runnable via `python -m ai_terminal`

## Project layout

```
AI-Agent/
├── ai_terminal/
│   ├── __init__.py      # public API
│   ├── __main__.py      # `python -m ai_terminal` entry point
│   ├── agent.py         # LLM + tool-calling loop
│   ├── cli.py           # interactive REPL + confirmation UI
│   ├── config.py        # settings from .env / environment
│   ├── executor.py      # subprocess command runner
│   └── safety.py        # dangerous-command detection
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## Quick start

### 1. Install dependencies

```powershell
cd C:\Users\test1\Desktop\AI-Agent
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell script execution is disabled, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use
> `.venv\Scripts\activate.bat` from `cmd.exe`.

### 2. Add your API key

```powershell
copy .env.example .env
notepad .env
```

Set at least:

```
OPENAI_API_KEY=sk-...your key...
```

### 3. Run it

```powershell
python -m ai_terminal
```

Or, after installing the package (`pip install -e .`), just run:

```powershell
aita
```

## Configuration (`.env`)

| Variable            | Default        | Description                                                                 |
|---------------------|----------------|-----------------------------------------------------------------------------|
| `OPENAI_API_KEY`    | *(required)*   | API key for the OpenAI-compatible endpoint.                                 |
| `AI_MODEL`          | `gpt-4o-mini`  | Model name passed to the API.                                               |
| `OPENAI_BASE_URL`   | *(OpenAI default)* | Override to use Azure, OpenRouter, LM Studio (`http://localhost:1234/v1`), Ollama (`http://localhost:11434/v1`), etc. |
| `AI_TEMPERATURE`    | `0.2`          | Sampling temperature. Lower = more deterministic.                           |
| `MAX_AUTO_STEPS`    | `5`            | Number of non-dangerous commands auto-approved per turn. `0` = always ask.  |

### Using a local model (Ollama example)

```
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
AI_MODEL=llama3.1
```

## Usage

Start the REPL and ask for things in natural language:

```
aita (AI-Agent)> list the largest files in this folder
aita (AI-Agent)> create a python project called demo with a hello world script
aita (AI-Agent)> show me the top 5 processes by memory usage
aita (AI-Agent)> find all .py files containing the word TODO
```

Slash commands:

| Command    | Action                          |
|------------|---------------------------------|
| `/help`    | Show help                       |
| `/clear`   | Clear conversation history      |
| `/cwd`     | Print current working directory |
| `/cd PATH` | Change working directory        |
| `/exit`    | Quit (also Ctrl+C / Ctrl+D)     |

## How it works

1. Your request is sent to the LLM with a system prompt describing the Windows environment and a single tool: `run_command`.
2. The model returns one or more tool calls (commands to run).
3. Each command is checked by the safety layer:
   - **Dangerous** → always asks for `y/N` confirmation.
   - **Safe** → auto-approved up to `MAX_AUTO_STEPS`, then asks.
4. The command runs via `cmd.exe /c` (or `powershell.exe -NoProfile -Command`), and stdout/stderr/exit code are fed back to the model.
5. The loop continues until the model stops calling tools and returns a final answer.

## Safety

This agent runs real commands on your real machine. It is **not** sandboxed. Mitigations:

- A denylist of destructive patterns triggers an explicit confirmation prompt.
- A per-turn auto-approve budget prevents runaway execution.
- The full command is always shown before it runs in interactive mode.

You are responsible for reviewing commands before approving them. Never give an AI agent access to a machine with data you cannot afford to lose.

## License

MIT