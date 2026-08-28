from cerbia.core.config import CerbIAConfig
from cerbia.core.runner import Runner
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def render_validation_summary(config: CerbIAConfig, runner: Runner, output_console: Console) -> None:
    """Render the established validation table and status panel.

    Args:
        config (CerbIAConfig): Validated configuration instance.
        runner (Runner): Runner instance initialized with the configuration.
        output_console (Console): Rich console for output.
    """
    table = Table(show_header=True, expand=True, border_style="green")
    table.add_column("Gate", style="bold cyan", no_wrap=True)
    table.add_column("Scanners", ratio=3)
    table.add_column("#", justify="right", style="dim")

    scanner_names = [type(scanner).__name__ for scanner in runner.gate.scanners]
    table.add_row(
        runner.gate.name,
        ", ".join(scanner_names),
        str(len(scanner_names)),
    )

    loader_status = "[green]yes[/green]" if config.loaders else "[yellow]no[/yellow]"

    output_console.print(
        Panel(
            table,
            title="[bold green]✓ Config valid[/bold green]",
            subtitle=f"1 gate(s) · loaders={loader_status}",
            border_style="green",
            padding=(0, 1),
        )
    )
