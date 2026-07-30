"""Interactive REPL for the AI terminal agent.

Provides a rich, colored terminal UI with:
- a prompt with the current working directory,
- streaming display of agent events (commands, output, answers),
- per-command confirmation with extra warnings for dangerous commands,
- slash commands for help, clear, exit, etc.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .agent import Agent, AgentEvent
from .config import PROVIDERS, Settings, load_settings
from .safety import SafetyVerdict


HELP_TEXT = """\
[bold cyan]AITA - AI Terminal Agent[/bold cyan]

Ask me to do something on your machine, e.g.:
  - "list the largest files in this folder"
  - "create a new python project called demo and add a hello world script"
  - "show me the top 5 processes by memory usage"
  - "find all .py files that contain the word TODO"

[bold]Slash commands:[/bold]
  /help     Show this help
  /clear    Clear conversation history
  /cwd      Show the current working directory
  /cd PATH  Change the working directory
  /exit     Quit the agent (also Ctrl+C or Ctrl+D)
"""


def _make_confirm(settings: Settings, console):
    """Build a confirmation callback honoring MAX_AUTO_STEPS + danger checks."""
    auto_budget = settings.max_auto_steps

    def confirm(command: str, verdict: SafetyVerdict) -> bool:
        nonlocal auto_budget

        if verdict.is_dangerous:
            console.print(
                f"[bold red]DANGEROUS:[/bold red] {verdict.reason}\n"
                f"[yellow]Command:[/yellow] {command}"
            )
            answer = console.input(
                "[bold red]Run this dangerous command? (y/N):[/bold red] "
            ).strip().lower()
            return answer in ("y", "yes")

        if auto_budget > 0:
            auto_budget -= 1
            return True

        console.print(f"[yellow]Command:[/yellow] {command}")
        answer = console.input(
            "[bold yellow]Run this command? (y/N/a=always):[/bold yellow] "
        ).strip().lower()
        if answer in ("a", "always"):
            auto_budget = settings.max_auto_steps
            return True
        return answer in ("y", "yes")

    return confirm


def _render_event(event: AgentEvent, console) -> None:
    if event.kind == "command":
        shell = event.extra.get("shell", "cmd")
        verdict: SafetyVerdict = event.extra.get("verdict")
        tag = "[bold magenta]CMD[/bold magenta]"
        if verdict and verdict.is_dangerous:
            tag = "[bold red]CMD(!)[/bold red]"
        console.print(f"{tag} ({shell}) {event.text}")
    elif event.kind == "output":
        rc = event.extra.get("returncode", "?")
        ok = event.extra.get("ok", False)
        color = "green" if ok else "red"
        console.print(
            f"[{color}]exit={rc}[/{color}]\n[dim]{event.text}[/dim]"
        )
    elif event.kind == "answer":
        console.print(f"\n[bold green]AITA:[/bold green] {event.text}\n")
    elif event.kind == "error":
        console.print(f"[bold red]ERROR:[/bold red] {event.text}")
    elif event.kind == "info":
        console.print(f"[dim]{event.text}[/dim]")


def _render_query_output(query: str, settings: Settings | None = None) -> int:
    try:
        from rich.console import Console
    except Exception as exc:
        print(f"Missing UI dependency (rich): {exc}")
        print("Run: pip install -r requirements.txt")
        return 2

    console = Console()
    settings = settings or load_settings()

    if not settings.is_configured:
        preset = PROVIDERS.get(settings.provider, PROVIDERS["groq"])
        key_env = preset["key_env"]
        console.print(
            f"[bold red]No API key found for provider '{settings.provider}'.[/bold red]\n"
            f"Set [bold]{key_env}=your-key[/bold] or [bold]OPENAI_API_KEY=your-key[/bold] and restart."
        )
        return 1

    cwd = Path.cwd()
    confirm = _make_confirm(settings, console)
    agent = Agent(settings, cwd=cwd, confirm=confirm)

    try:
        for event in agent.run(query):
            _render_event(event, console)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        return 0

    return 0


def run_repl(settings: Settings | None = None) -> int:
    """Start the interactive REPL. Returns an exit code."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt
    except Exception as exc:
        print(f"Missing UI dependency (rich): {exc}")
        print("Run: pip install -r requirements.txt")
        return 2

    console = Console()
    settings = settings or load_settings()

    if not settings.is_configured:
        preset = PROVIDERS.get(settings.provider, PROVIDERS["groq"])
        key_env = preset["key_env"]
        free_lines = []
        for name, info in PROVIDERS.items():
            marker = " [green](current)[/green]" if name == settings.provider else ""
            free_lines.append(f"  - [bold]{name:10}[/bold] {info['label']}{marker}")
        console.print(
            Panel(
                f"[bold red]No API key found for provider '{settings.provider}'.[/bold red]\n\n"
                f"1. Copy .env.example to .env\n"
                f"2. Set [bold]{key_env}=your-key[/bold]  (get one free at the link above)\n"
                f"3. Optionally set [bold]AI_PROVIDER={settings.provider}[/bold]\n"
                f"4. Restart AITA.\n\n"
                "[bold]Free providers supported:[/bold]\n"
                + "\n".join(free_lines)
                + "\n\nSee README.md for details.",
                title="Configuration needed",
                border_style="red",
            )
        )
        return 1

    cwd = Path.cwd()
    confirm = _make_confirm(settings, console)
    agent = Agent(settings, cwd=cwd, confirm=confirm)

    console.print(
        Panel(
            f"[bold cyan]AITA[/bold cyan] - AI Terminal Agent\n"
            f"Provider: [magenta]{settings.provider}[/magenta]  "
            f"Model: [green]{settings.model}[/green]  "
            f"CWD: [blue]{cwd}[/blue]\n"
            f"Type /help for commands. Ctrl+C or /exit to quit.",
            border_style="cyan",
        )
    )

    while True:
        try:
            prompt_text = f"[bold cyan]aita ({cwd.name})>[/bold cyan] "
            user_input = Prompt.ask(prompt_text, console=console).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            return 0

        if not user_input:
            continue

        # Slash commands
        if user_input.startswith("/"):
            cmd, *rest = user_input[1:].split(maxsplit=1)
            arg = rest[0] if rest else ""
            if cmd in ("exit", "quit"):
                console.print("[dim]Goodbye.[/dim]")
                return 0
            if cmd == "help":
                console.print(Panel(HELP_TEXT, border_style="cyan"))
                continue
            if cmd == "clear":
                confirm = _make_confirm(settings, console)
                agent = Agent(settings, cwd=cwd, confirm=confirm)
                console.print("[dim]Conversation cleared.[/dim]")
                continue
            if cmd == "cwd":
                console.print(str(cwd))
                continue
            if cmd == "cd":
                new_cwd = (cwd / arg).resolve() if arg else Path.home()
                if new_cwd.exists() and new_cwd.is_dir():
                    cwd = new_cwd
                    agent = Agent(settings, cwd=cwd, confirm=confirm)
                    console.print(f"[dim]CWD -> {cwd}[/dim]")
                else:
                    console.print(f"[red]Not a directory: {new_cwd}[/red]")
                continue
            console.print(f"[red]Unknown command: /{cmd}[/red]")
            continue

        try:
            for event in agent.run(user_input):
                _render_event(event, console)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user.[/yellow]")
        except Exception as exc:
            console.print(f"[bold red]Unexpected error:[/bold red] {exc}")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    if argv:
        if argv[0] in ("-h", "--help"):
            print("Usage: aita tell <query> | aita <query> | aita")
            return 0

        query = " ".join(argv)
        if argv[0] == "tell":
            query = " ".join(argv[1:])

        if not query.strip():
            print("Usage: aita tell <query> or tell <query>")
            return 2

        return _render_query_output(query)

    return run_repl()


if __name__ == "__main__":
    sys.exit(main())