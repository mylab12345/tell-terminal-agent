# Tell

Tell is a lightweight, cross-platform terminal Q&A assistant. Ask a question in plain English and it gives a clear answer in your terminal.

**Answer-only by design:** Tell does **not** run commands, read local files, write files, edit your project, install packages, or operate your machine. If a question needs local context, paste the relevant text or command output into Tell.

Works on **Linux**, **macOS**, and **Windows**. Uses any **OpenAI-compatible** chat model (OpenAI, Groq, Gemini, OpenRouter, Ollama, LM Studio, etc.).

## Features

- 💬 **Answers only** — focused natural-language responses, no autonomous execution
- 🔒 **No local actions** — Tell never runs shell commands or changes files
- 🎨 **Mission-grade Rich UI** — polished terminal panels for answers, configuration help, and errors
- 🌍 **Cross-platform** — works on Linux, macOS, and Windows terminals
- 🔌 **Multi-provider** — built-in presets for Groq, Gemini, OpenRouter, Cerebras, SambaNova, OpenAI
- 📦 **Installable** — `pip install -e .` gives you the `tell` console command

## Project layout

```
tell-terminal-agent/
├── ai_terminal/
│   ├── __init__.py      # public API + version
│   ├── __main__.py      # `python -m ai_terminal` entry point
│   ├── agent.py         # answer-only LLM conversation loop
│   ├── cli.py           # interactive REPL + one-shot CLI
│   ├── config.py        # settings from .env / environment
│   ├── executor.py      # command-runner utility retained for compatibility/tests
│   ├── safety.py        # command-safety utility retained for compatibility/tests
│   └── tools.py         # tool schemas retained for compatibility/tests
├── tests/
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

### 3. Ask with `tell`

**Interactive REPL:**
```bash
tell
# or: python -m ai_terminal
```

**One-shot query:**
```bash
tell "what does this error mean?"
tell "how do I list the largest files in a folder?"
tell "write a safe checklist for debugging a failing test suite"
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
| `COMMAND_TIMEOUT` | `120` | Retained for compatibility; unused by answer-only Tell |

### Using a local model (Ollama example)

```
AI_PROVIDER=openai
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
AI_MODEL=llama3.1
```

## Usage examples

```
tell (project)> summarize this pasted stack trace
tell (project)> what command lists the largest files in this folder?
tell (project)> explain what pytest is reporting here: <paste output>
tell (project)> suggest a safe git workflow before refactoring
tell (project)> how do I check which process is using port 8000?
tell (project)> turn this error message into a debugging checklist
```

## Answer-only behavior

Tell sends your query to the configured model without tool access. It will not inspect your repository or execute anything locally.

If you ask Tell to do something on your machine, it should respond with guidance instead, for example:

- commands you can choose to run yourself
- what output to paste back for help
- safety warnings for risky operations
- a concise explanation of assumptions

## Slash commands

| Command | Action |
|---|---|
| `/help` | Show help |
| `/clear` | Clear conversation history |
| `/cwd` | Print current working directory label |
| `/cd PATH` | Change the prompt's working directory label/context |
| `/exit` | Quit (also Ctrl+C / Ctrl+D) |

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Safety

Tell is safer than an execution agent because it does not run commands or edit files. Still, review any command it suggests before running it yourself, especially commands that delete files, change permissions, install software, or modify system settings.

## License

MIT
