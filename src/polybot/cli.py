"""CLI entrypoint: `python -m polybot [--strategy ... | --serve]`."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from .api import create_app
from .bot import run_bot
from .config import get_settings
from .logging_utils import get_logger

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()
log = get_logger("polybot.cli")


@app.command()
def main(
    strategy: str = typer.Option("momentum", "--strategy", help="momentum | mean-revert | news-edge"),
    serve: bool = typer.Option(False, "--serve", help="Run as FastAPI backend (for the Mini App)"),
    host: str = typer.Option(None, "--host"),
    port: int = typer.Option(None, "--port"),
    interval: float = typer.Option(15.0, "--interval", help="Seconds between scans"),
):
    """Run the Polybot bot or backend."""
    settings = get_settings()
    log.info("polybot starting (strategy=%s serve=%s)", strategy, serve)
    if serve:
        import uvicorn
        h = host or settings.host
        p = port or settings.port
        uvicorn.run(create_app(), host=h, port=p, log_level=settings.log_level.lower())
        return
    try:
        asyncio.run(run_bot(strategy, scan_interval=interval))
    except KeyboardInterrupt:
        log.info("bye")


if __name__ == "__main__":
    app()
