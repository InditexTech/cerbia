from pathlib import Path
from typing import Annotated

import typer
from cerbia.core.exceptions import CerbIAError
from cerbia.core.runner import Runner
from rich.console import Console

from ..config import load_config_from_yaml
from ..logging import configure_logging
from ._ui import render_validation_summary

app = typer.Typer(no_args_is_help=True)


@app.command()
def validate(
    config: Annotated[Path, typer.Argument(help="Path to a single YAML configuration file.")],
    log_level: Annotated[
        str | None, typer.Option("--log-level", help="Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL).")
    ] = None,
    log_file: Annotated[
        Path | None, typer.Option("--log-file", help="Write logs to this file instead of stderr.")
    ] = None,
) -> None:
    """Validate a single YAML configuration file and report gate structure.

    Raises:
        typer.Exit: Raised with a non-zero code when the configuration path is invalid or the configuration fails
            validation.
    """
    err_console = Console(stderr=True)

    if not config.exists():
        err_console.print("[red]Error:[/red] configuration file not found.")
        raise typer.Exit(code=2)

    cfg = load_config_from_yaml(config, err_console)
    configure_logging(log_level, log_file, err_console)

    try:
        runner = Runner(cfg)
        render_validation_summary(cfg, runner, err_console)

    except CerbIAError as exc:
        err_console.print("[red bold]✗ Invalid config[/red bold]")
        raise typer.Exit(code=1) from exc
    except TypeError as exc:
        err_console.print("[red bold]✗ Config validation failed.[/red bold]")
        raise typer.Exit(code=2) from exc
