from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json

console = Console()


def print_message(role: str, content: str) -> None:
    color = "cyan" if role == "assistant" else "green"
    console.print(Panel(content, title=f"[bold {color}]{role}[/]", border_style=color))


def print_tool_call(tool_name: str, inputs: dict) -> None:
    console.print(
        Panel(
            Syntax(json.dumps(inputs, indent=2), "json"),
            title=f"[bold yellow]Tool Call: {tool_name}[/]",
            border_style="yellow",
        )
    )


def print_error(msg: str) -> None:
    console.print(f"[bold red]ERROR:[/] {msg}")
