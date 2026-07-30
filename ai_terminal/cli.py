"""Interactive REPL and one-shot CLI for the AI terminal agent.

Provides a rich, colored terminal UI with:
- a prompt with the current working directory,
- streaming display of agent events (commands, output, answers),
- per-command confirmation with extra warnings for dangerous commands,
- slash commands for help, clear, exit, etc.

Works on Linux, macOS, and Windows.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .agent import Agent, AgentEvent
from .config import PROVIDERS, Settings, load_settings
from .safety import SafetyVerdict

logger = logging.getLogger(__name__)

HELP_TEXT = """\
[bold cyan]AI Terminal Agent[/bold cyan]

Ask me to do something on your machine, e.g.:
  - "list the largest files in this folder"
  - "create a new python project called demo"
  - "find all .py files that contain the word TODO"
  - "explain what this code does and suggest improvements"
  - "run the tests and fix any failures"

[bold]Slash commands:[/bold]
  /help     Show this help
  /clear    Clear conversation history
  /cwd      Show the current working directory
  /cd PATH  Change the working directory
  /exit     Quit the agent (also Ctrl+C or Ctrl+D)
"""


# ---------------------------------------------------------------------------
# Confirmation callback
# ---------------------------------------------------------------------------

def _make_confirm(settings: Settings, console):
    """Build a confirmation callback honoring MAX_AUTO_STEPS + danger checks."""
    auto_budget = settings.max_auto_steps

    def confirm(command: str, verdict: SafetyVerdict) -> bool:
        nonlocal auto_budget

        if verdict.is_dangerous:
            console.print(
                f"[bold red]⚠  DANGEROUS:[/bold red] {verdict.reason}\n"
                f"[yellow]Command:[/yellow] {command}"
            )
            answer = (
                console.input(
                    "[bold red]Run this dangerous command? (y/N): [/bold red]"
                )
                .strip()
                .lower()
            )
            return answer in ("y", "yes")

        if auto_budget > 0:
            auto_budget -= 1
            return True

        console.print(f"[yellow]Command:[/yellow] {command}")
        answer = (
            console.input(
                "[bold yellow]Run this command? (y/N/a=always): [/bold yellow]"
            )
            .strip()
            .lower()
        )
        if answer in ("a", "always"):
            auto_budget = settings.max_auto_steps
            return True
        return answer in ("y", "yes")

    return confirm


# ---------------------------------------------------------------------------
# Event rendering
# ---------------------------------------------------------------------------

def _render_event(event: AgentEvent, console) -> None:
    """Render a single agent event to the console."""
    if event.kind == "command":
        shell = event.extra.get("shell", "auto")
        verdict: SafetyVerdict | None = event.extra.get("verdict")
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
        console.print(f"\n[bold green]Agent:[/bold green] {event.text}\n")
    elif event.kind == "error":
        console.print(f"[bold red]ERROR:[/bold red] {event.text}")
    elif event.kind == "info":
        console.print(f"[dim]{event.text}[/dim]")
    elif event.kind == "file_op":
        console.print(f"[bold blue]FILE:[/bold blue] {event.text}")


# ---------------------------------------------------------------------------
# One-shot query
# ---------------------------------------------------------------------------

def _render_query_output(query: str, settings: Settings | None = None) -> int:
    """Run a single query and print the output."""
    try:
        from rich.console import Console
    except ImportError as exc:
        print(f"Missing dependency (rich): {exc}")
        print("Run: pip install -r requirements.txt")
        return 2

    console = Console()
    settings = settings or load_settings()

    if not settings.is_configured:
        _print_config_error(settings, console)
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


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def run_repl(settings: Settings | None = None) -> int:
    """Start the interactive REPL.  Returns an exit code."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt
    except ImportError as exc:
        print(f"Missing dependency (rich): {exc}")
        print("Run: pip install -r requirements.txt")
        return 2

    console = Console()
    settings = settings or load_settings()

    if not settings.is_configured:
        _print_config_error(settings, console)
        return 1

    cwd = Path.cwd()
    confirm = _make_confirm(settings, console)
    agent = Agent(settings, cwd=cwd, confirm=confirm)

    console.print(
        Panel(
            f"[bold cyan]AI Terminal Agent[/bold cyan]\n"
            f"Provider: [magenta]{settings.provider}[/magenta]  "
            f"Model: [green]{settings.model}[/green]  "
            f"CWD: [blue]{cwd}[/blue]\n"
            f"Type /help for commands. Ctrl+C or /exit to quit.",
            border_style="cyan",
        )
    )

    while True:
        try:
            prompt_text = f"[bold cyan]agent ({cwd.name})>[/bold cyan] "
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
                    console.print(f"[dim]CWD → {cwd}[/dim]")
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
            logger.exception("Unexpected error in agent loop")
            console.print(f"[bold red]Unexpected error:[/bold red] {exc}")


# ---------------------------------------------------------------------------
# Config error helper
# ---------------------------------------------------------------------------

def _print_config_error(settings: Settings, console) -> None:
    """Print a helpful configuration error message."""
    try:
        from rich.panel import Panel
    except ImportError:
        print(f"No API key configured for provider '{settings.provider}'.")
        return

    preset = PROVIDERS.get(settings.provider, PROVIDERS["groq"])
    key_env = preset["key_env"]

    free_lines: list[str] = []
    for name, info in PROVIDERS.items():
        marker = " [green](current)[/green]" if name == settings.provider else ""
        free_lines.append(
            f"  - [bold]{name:10}[/bold] {info['label']}{marker}"
        )

    console.print(
        Panel(
            f"[bold red]No API key found for provider "
            f"'{settings.provider}'.[/bold red]\n\n"
            f"1. Copy .env.example to .env\n"
            f"2. Set [bold]{key_env}=your-key[/bold]\n"
            f"3. Optionally set [bold]AI_PROVIDER={settings.provider}[/bold]\n"
            f"4. Restart the agent.\n\n"
            "[bold]Supported providers:[/bold]\n"
            + "\n".join(free_lines)
            + "\n\nSee README.md for details.",
            title="Configuration needed",
            border_style="red",
        )
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the appropriate mode."""
    argv = argv if argv is not None else sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="tell",
        description="AI Terminal Agent — run coding tasks from natural language.",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Natural-language query to run (omit for interactive REPL).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    # Strip leading "tell" if present (for backward compat: `aita tell ...`)
    query_parts = args.query or []
    if query_parts and query_parts[0].lower() == "tell":
        query_parts = query_parts[1:]

    query = " ".join(query_parts).strip()

    if query:
        return _render_query_output(query)

    return run_repl()


if __name__ == "__main__":
    sys.exit(main())
