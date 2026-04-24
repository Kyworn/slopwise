"""Command-line interface for slopwise."""

import click
from pathlib import Path


@click.group()
def main():
    """slopwise: semantic firmware diff via multi-agent LLM analysis."""
    pass


@main.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
@click.option("--config", type=click.Path(exists=True), required=True, help="Path to config.yaml")
@click.option("-o", "--output", type=click.Path(), default="report.md", help="Output report path")
def diff(file_a: str, file_b: str, config: str, output: str):
    """Analyze semantic differences between two binaries.

    FILE_A: Path to original binary
    FILE_B: Path to modified binary
    """
    raise NotImplementedError("slopwise is pre-alpha, core pipeline not yet implemented")


if __name__ == "__main__":
    main()
