import logging
from pathlib import Path

import typer
import yaml
from cerbia.core.config import CerbIAConfig
from cerbia.core.exceptions import CerbIAConfigError, CerbIAError
from rich.console import Console
from yaml.error import YAMLError

logger = logging.getLogger(__name__)


def load_config_from_yaml(path: Path, output_console: Console) -> CerbIAConfig:
    """Load and validate configuration from a YAML file.

    Args:
        path (Path): Filesystem path to the config YAML file.
        output_console (Console): Rich console for outputting warnings and errors.

    Returns:
        CerbIAConfig: Validated configuration instance.

    Raises:
        cerbia.core.exceptions.CerbIAConfigError: If the file does not contain a YAML mapping.
    """
    try:
        logger.debug("Loading configuration")
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise CerbIAConfigError(f"Expected YAML mapping, got {type(raw).__name__}")

        config = CerbIAConfig.model_validate(raw)
        logger.debug("Configuration loaded")

        return config

    except FileNotFoundError as exc:
        output_console.print(f"[red]Error:[/red] config file not found: {path}")
        raise typer.Exit(code=2) from exc
    except IsADirectoryError as exc:
        output_console.print(f"[red]Error:[/red] config path is a directory: {path}")
        raise typer.Exit(code=2) from exc
    except PermissionError as exc:
        output_console.print(f"[red]Error:[/red] permission denied reading config file: {path}")
        raise typer.Exit(code=2) from exc
    except YAMLError as exc:
        output_console.print(f"[red]Error:[/red] invalid YAML in config file: {path}")
        raise typer.Exit(code=2) from exc
    except CerbIAError as exc:
        output_console.print(f"[red]Error:[/red] invalid configuration in file: {path}")
        raise typer.Exit(code=2) from exc
