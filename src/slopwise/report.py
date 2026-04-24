"""Report generation and formatting."""

from pathlib import Path


def render_markdown(changes: list, output_path: Path) -> None:
    """Render analyzed changes to markdown report.

    Args:
        changes: List of change dicts with keys: name, category, summary, risk
        output_path: Path to write report.md
    """
    raise NotImplementedError("render_markdown() pending implementation")
