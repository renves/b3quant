"""
Command Line Interface for b3quant.

Provides terminal-based access to download and parse B3 market data.

Examples:
    Download yearly data:
        $ b3quant download --year 2024

    Download monthly data:
        $ b3quant download --year 2024 --month 11

    Download daily data:
        $ b3quant download --year 2024 --month 12 --day 20

    Download multiple years:
        $ b3quant download --start-year 2020 --end-year 2024

    Export to Parquet:
        $ b3quant download --year 2024 --output-format parquet
"""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import B3Quant, __version__

app = typer.Typer(
    name="b3quant",
    help="CLI for downloading and parsing B3 (Brazilian Stock Exchange) market data",
    add_completion=False,
)

console = Console()


class InstrumentType(str, Enum):
    """Instrument type enum for CLI."""

    OPTIONS = "options"
    STOCKS = "stocks"
    ALL = "all"


class OutputFormat(str, Enum):
    """Output format enum for CLI."""

    CSV = "csv"
    PARQUET = "parquet"


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"b3quant version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging"),
):
    """
    b3quant - Brazilian Stock Exchange (B3) market data downloader and parser.

    Download historical COTAHIST files and parse them into structured formats.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@app.command()
def download(
    year: int | None = typer.Option(
        None, "--year", "-y", help="Year to download (e.g., 2024)"
    ),
    month: int | None = typer.Option(
        None, "--month", "-m", help="Month to download (1-12)"
    ),
    day: int | None = typer.Option(None, "--day", "-d", help="Day to download (1-31)"),
    start_year: int | None = typer.Option(
        None, "--start-year", help="Start year for range download"
    ),
    end_year: int | None = typer.Option(
        None, "--end-year", help="End year for range download"
    ),
    instrument: InstrumentType = typer.Option(
        InstrumentType.OPTIONS,
        "--instrument",
        "-i",
        help="Type of instrument to download",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.CSV, "--output-format", "-f", help="Output file format"
    ),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Output directory for processed data"
    ),
    cache_dir: Path | None = typer.Option(
        None, "--cache-dir", "-c", help="Cache directory for raw files"
    ),
    force: bool = typer.Option(
        False, "--force", help="Force re-download even if cached"
    ),
):
    """
    Download and parse B3 market data.

    Examples:

        # Download 2024 options data
        $ b3quant download --year 2024

        # Download November 2024 stocks
        $ b3quant download --year 2024 --month 11 --instrument stocks

        # Download multiple years
        $ b3quant download --start-year 2020 --end-year 2024

        # Export to Parquet
        $ b3quant download --year 2024 --output-format parquet
    """
    try:
        # Initialize B3Quant client
        b3 = B3Quant(cache_dir=str(cache_dir) if cache_dir else "./data/raw")

        # Determine download mode
        if start_year and end_year:
            # Range download
            _download_range(
                b3,
                start_year,
                end_year,
                instrument,
                output_format,
                output_dir,
                force,
            )
        elif year:
            # Single download
            _download_single(
                b3, year, month, day, instrument, output_format, output_dir, force
            )
        else:
            # Default: current year
            current_year = datetime.now().year
            console.print(
                f"[yellow]No year specified, downloading current year ({current_year})[/yellow]"
            )
            _download_single(
                b3,
                current_year,
                None,
                None,
                instrument,
                output_format,
                output_dir,
                force,
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def _download_single(
    b3: B3Quant,
    year: int,
    month: int | None,
    day: int | None,
    instrument: InstrumentType,
    output_format: OutputFormat,
    output_dir: Path | None,
    force: bool,
):
    """Download a single period."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Download data
        if instrument == InstrumentType.OPTIONS:
            task = progress.add_task(
                f"Downloading options for {year}/{month or 'all'}/{day or 'all'}...",
                total=None,
            )
            df = b3.get_options(year=year, month=month, day=day, force_download=force)
        elif instrument == InstrumentType.STOCKS:
            task = progress.add_task(
                f"Downloading stocks for {year}/{month or 'all'}/{day or 'all'}...",
                total=None,
            )
            df = b3.get_stocks(year=year, month=month, day=day, force_download=force)
        else:
            task = progress.add_task(
                f"Downloading all data for {year}/{month or 'all'}/{day or 'all'}...",
                total=None,
            )
            df = b3.get_all(year=year, month=month, day=day, force_download=force)

        progress.remove_task(task)

    # Display summary
    _display_summary(df, year, month, day, instrument)

    # Export if output_dir specified
    if output_dir:
        _export_data(df, year, month, day, instrument, output_format, output_dir)


def _download_range(
    b3: B3Quant,
    start_year: int,
    end_year: int,
    instrument: InstrumentType,
    output_format: OutputFormat,
    output_dir: Path | None,
    force: bool,
):
    """Download a range of years."""
    console.print(
        f"[bold blue]Downloading {instrument.value} from {start_year} to {end_year}[/bold blue]"
    )

    for year in range(start_year, end_year + 1):
        _download_single(
            b3, year, None, None, instrument, output_format, output_dir, force
        )


def _display_summary(
    df,
    year: int,
    month: int | None,
    day: int | None,
    instrument: InstrumentType,
):
    """Display download summary."""
    table = Table(title=f"{instrument.value.upper()} Data Summary")

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Period", f"{year}/{month or 'all'}/{day or 'all'}")
    table.add_row("Records", f"{len(df):,}")

    if instrument == InstrumentType.OPTIONS:
        calls = len(df[df["instrument_type"] == "CALL"])
        puts = len(df[df["instrument_type"] == "PUT"])
        table.add_row("Calls", f"{calls:,}")
        table.add_row("Puts", f"{puts:,}")

        if "underlying" in df.columns:
            underlyings = df["underlying"].nunique()
            table.add_row("Underlyings", f"{underlyings:,}")

    if "volume" in df.columns:
        total_volume = df["volume"].sum()
        table.add_row("Total Volume (BRL)", f"R$ {total_volume:,.2f}")

    console.print(table)


def _export_data(
    df,
    year: int,
    month: int | None,
    day: int | None,
    instrument: InstrumentType,
    output_format: OutputFormat,
    output_dir: Path,
):
    """Export data to file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    if day:
        filename = f"{instrument.value}_{year}_{month:02d}_{day:02d}"
    elif month:
        filename = f"{instrument.value}_{year}_{month:02d}"
    else:
        filename = f"{instrument.value}_{year}"

    if output_format == OutputFormat.CSV:
        filepath = output_dir / f"{filename}.csv"
        df.to_csv(filepath, index=False)
    else:
        filepath = output_dir / f"{filename}.parquet"
        df.to_parquet(filepath, index=False, compression="snappy")

    console.print(f"[bold green]✓[/bold green] Exported to {filepath}")


@app.command()
def info():
    """Show b3quant configuration and system information."""
    from . import config

    table = Table(title="b3quant Configuration")

    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Version", __version__)
    table.add_row("B3 Base URL", config.B3_BASE_URL)
    table.add_row("Cache Backend", config.CACHE_BACKEND)
    table.add_row("Cache TTL (days)", str(config.CACHE_TTL_DAYS))
    table.add_row("Max Retry Attempts", str(config.MAX_RETRY_ATTEMPTS))
    table.add_row("Show Progress", str(config.SHOW_PROGRESS))

    console.print(table)


if __name__ == "__main__":
    app()
