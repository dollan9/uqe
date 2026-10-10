"""Typer command-line interface for the AV Editor Agent.

Entrypoint registered in ``pyproject.toml`` as ``av-editor``. Commands are
thin wrappers: heavy modules (pipeline, exports) are imported lazily inside
each command so ``--help`` stays fast and import-safe on a bare install.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from av_editor import __version__
from av_editor.errors import AVEditorError

app = typer.Typer(
    name="av-editor",
    help="Vision-powered autonomous AI video editing agent.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _fail(message: str) -> None:
    console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print the package version and exit."""
    console.print(f"av-editor {__version__}")


@app.command()
def doctor() -> None:
    """Check external binaries and optional capabilities; report status."""
    from av_editor.core.subprocess_runner import SubprocessRunner

    runner = SubprocessRunner()
    table = Table(title="Environment check")
    table.add_column("Binary", style="cyan")
    table.add_column("Status")
    found_any = False
    for binary, hint in (
        ("ffmpeg", "install ffmpeg (apt/brew)"),
        ("ffprobe", "ships with ffmpeg"),
    ):
        path = runner.which(binary)
        if path:
            found_any = True
            table.add_row(binary, f"[green]ok[/green] ({path})")
        else:
            table.add_row(binary, f"[yellow]missing[/yellow] — {hint}")
    console.print(table)
    if not found_any:
        console.print("[yellow]warning:[/yellow] no media binaries found; "
                      "ingest/render commands will fail until installed.")


@app.command()
def config_show(
    config: str = typer.Option("config.yaml", "--config", "-c", help="Path to YAML config."),
) -> None:
    """Load and validate a configuration file, then print the resolved model."""
    from pathlib import Path

    from av_editor.settings import PipelineConfig

    try:
        cfg = PipelineConfig.from_yaml(Path(config))
    except AVEditorError as exc:
        _fail(str(exc))
    console.print(cfg.model_dump_json(indent=2))


@app.command()
def run(
    project: str = typer.Argument(..., help="Project directory containing config.yaml."),
    brief: str = typer.Option(None, "--brief", help="Editorial brief text or @file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only; do not render."),
) -> None:
    """Execute the full edit pipeline for a project (plan → analyze → cut → QA).

    Note: a fully wired end-to-end run also requires analysis/cut/QA nodes to
    be registered; until that high-level runner exists this command loads and
    validates the config and reports readiness.
    """
    from pathlib import Path

    project_dir = Path(project)
    cfg_path = project_dir / "config.yaml"
    if not project_dir.is_dir():
        _fail(f"project directory not found: {project_dir}")
    # Lazy imports keep `av-editor --help` import-safe without heavy deps.
    from av_editor.settings import PipelineConfig

    try:
        PipelineConfig.from_yaml(cfg_path)
    except AVEditorError as exc:
        _fail(str(exc))
    if dry_run:
        console.print(f"[cyan]dry-run:[/cyan] config valid for {cfg_path}; no stages executed.")
        return
    console.print("[yellow]not-implemented:[/yellow] full pipeline execution is not yet "
                  "wired into the CLI; use the Orchestrator API directly.")
    raise typer.Exit(code=2)


def app_entry() -> None:  # pragma: no cover - thin wrapper
    """Console-script entrypoint referenced by ``[project.scripts]``."""
    app()


if __name__ == "__main__":  # pragma: no cover
    app_entry()
