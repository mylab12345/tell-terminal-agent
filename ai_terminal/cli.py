"""Interactive REPL and one-shot CLI for Tell.

Provides a polished, mission-control style terminal UI with:
- a prompt with the current working directory label,
- structured rendering of answers and errors,
- clear answer-only guidance,
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

logger = logging.getLogger(__name__)

APP_NAME = "Tell"
APP_TAGLINE = "Answer-only terminal assistant"

HELP_TEXT = """\
[bold cyan]Tell[/bold cyan]
[dim]Ask questions and get clear answers. Tell never runs local commands.[/dim]

[bold]How to ask:[/bold]
  - "what does this error mean?"
  - "how do I list the largest files in a folder?"
  - "explain this pasted stack trace"
  - "what is a safe git workflow before refactoring?"
  - "write a checklist for debugging failing tests"

[bold]Answer-only protocol:[/bold]
  1. Tell gives answers only; it does not run commands or edit files.
  2. If local context is needed, paste files, logs, or command output.
  3. Suggested commands are instructions for you to review and run yourself.
  4. Risky suggestions should be clearly labeled before you act.

[bold]Slash commands:[/bold]
  /help     Show this help
  /clear    Clear conversation history
  /cwd      Show the current working directory
  /cd PATH  Change the working directory
  /exit     Quit Tell (also Ctrl+C or Ctrl+D)
"""


# ---------------------------------------------------------------------------
# Small rendering helpers
# ---------------------------------------------------------------------------

def _cwd_label(cwd: Path) -> str:
    """Return a compact, friendly label for a current working directory."""
    return cwd.name or str(cwd)


# ---------------------------------------------------------------------------
# Event rendering
# ---------------------------------------------------------------------------

def _render_event(event: AgentEvent, console) -> None:
    """Render a non-streaming event to the console."""
    from rich.panel import Panel
    from rich.text import Text

    if event.kind == "answer":
        _render_agent_events([event], console)
        return

    if event.kind == "error":
        console.print(
            Panel(
                Text(event.text),
                title="[bold red]Anomaly detected[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        return

    if event.kind == "info":
        console.print(
            Panel(
                Markdown(event.text.strip() or "Note"),
                title="[bold blue]Note[/bold blue]",
                border_style="blue",
                expand=False,
            )
        )
        return

    console.print(Text(event.text))


def _render_agent_events(events, console) -> None:
    """Render an answer as it streams, using only top and bottom rules.

    ``Live`` redraws within the terminal's current width, so ordinary prose and
    Markdown reflow when the terminal is narrow without the side borders and
    padding imposed by a panel.
    """
    from rich.console import Group
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.rule import Rule

    def answer_view(answer: str):
        return Group(
            Rule("[bold green]✓ Answer[/bold green]", style="green"),
            Markdown(answer or "…"),
            Rule(style="green"),
        )

    parts: list[str] = []
    live = None
    deferred_events: list[AgentEvent] = []
    try:
        for event in events:
            if event.kind == "answer_delta":
                parts.append(event.text)
            elif event.kind == "answer":
                # Streaming sends a final answer event for history/API users;
                # do not append it after already-rendered delta text.
                if not parts:
                    parts.append(event.text)
            else:
                deferred_events.append(event)
                continue

            if live is None:
                live = Live(
                    answer_view("".join(parts)),
                    console=console,
                    refresh_per_second=12,
                    transient=False,
                    vertical_overflow="visible",
                )
                live.start()
            else:
                live.update(answer_view("".join(parts)))
    finally:
        if live is not None:
            live.stop()

    for event in deferred_events:
        _render_event(event, console)


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
    agent = Agent(settings, cwd=cwd)

    console.print(
        f"[bold cyan]● {APP_NAME}[/bold cyan] "
        f"[dim]({settings.provider}/{settings.model}, cwd={cwd})[/dim]"
    )

    try:
        _render_agent_events(agent.run(query), console)
    except KeyboardInterrupt:
        console.print("\n[yellow]Mission interrupted by user.[/yellow]")

    return 0


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def run_repl(settings: Settings | None = None) -> int:
    """Start the interactive REPL.  Returns an exit code."""
    try:
        from rich.console import Console
        from rich.panel import Panel
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
    agent = Agent(settings, cwd=cwd)

    console.print(
        Panel(
            f"[bold cyan]{APP_NAME}[/bold cyan]\n"
            f"[dim]{APP_TAGLINE}[/dim]\n\n"
            f"Provider: [magenta]{settings.provider}[/magenta]  "
            f"Model: [green]{settings.model}[/green]\n"
            f"CWD: [blue]{cwd}[/blue]\n"
            f"Mode: [green]answers only[/green] — "
            f"[yellow]no local commands[/yellow], "
            f"[yellow]no file changes[/yellow]\n\n"
            f"Type [bold]/help[/bold] for commands. Ctrl+C or /exit to quit.",
            title="🚀 Launch Console",
            border_style="cyan",
        )
    )

    while True:
        try:
            prompt_text = (
                f"[bold cyan]tell[/bold cyan] "
                f"[dim]({_cwd_label(cwd)})[/dim] "
                f"[bold cyan]>[/bold cyan] "
            )
            user_input = console.input(prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Mission closed. Goodbye.[/dim]")
            return 0

        if not user_input:
            continue

        # Slash commands
        if user_input.startswith("/"):
            cmd, *rest = user_input[1:].split(maxsplit=1)
            arg = rest[0] if rest else ""
            if cmd in ("exit", "quit"):
                console.print("[dim]Mission closed. Goodbye.[/dim]")
                return 0
            if cmd == "help":
                console.print(Panel(HELP_TEXT, title="Help", border_style="cyan"))
                continue
            if cmd == "clear":
                agent = Agent(settings, cwd=cwd)
                console.print("[dim]Conversation cleared. Fresh mission context loaded.[/dim]")
                continue
            if cmd == "cwd":
                console.print(f"[blue]{cwd}[/blue]")
                continue
            if cmd == "cd":
                new_cwd = (cwd / arg).resolve() if arg else Path.home()
                if new_cwd.exists() and new_cwd.is_dir():
                    cwd = new_cwd
                    agent = Agent(settings, cwd=cwd)
                    console.print(f"[dim]CWD → {cwd}[/dim]")
                else:
                    console.print(f"[red]Not a directory: {new_cwd}[/red]")
                continue
            console.print(f"[red]Unknown command: /{cmd}[/red]")
            continue

        try:
            _render_agent_events(agent.run(user_input), console)
        except KeyboardInterrupt:
            console.print("\n[yellow]Mission interrupted by user.[/yellow]")
        except Exception as exc:
            logger.exception("Unexpected error in Tell loop")
            console.print(
                Panel(
                    str(exc),
                    title="[bold red]Unexpected anomaly[/bold red]",
                    border_style="red",
                    expand=False,
                )
            )


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
            f"4. Restart Tell.\n\n"
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
        description=(
            "Tell — an answer-only terminal assistant for "
            "natural-language questions."
        ),
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Natural-language question to answer (omit for interactive REPL).",
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

    # Strip leading "tell" if users paste the full command into the query.
    query_parts = args.query or []
    if query_parts and query_parts[0].lower() == "tell":
        query_parts = query_parts[1:]

    query = " ".join(query_parts).strip()

    if query:
        return _render_query_output(query)

    return run_repl()


if __name__ == "__main__":
    sys.exit(main())
