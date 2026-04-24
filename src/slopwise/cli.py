"""Command-line interface for slopwise."""

import asyncio
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from .agents.analyzer import FunctionAnalyzer
from .agents.clusterer import ChangeClusterer
from .agents.critic import ChangeCritic
from .config import load_config
from .decompile import Decompiler
from .diff import DiffEngine
from .llm import LLMClient
from .report import render_markdown

# Setup logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("slopwise")
console = Console()


async def _run_diff(file_a: str, file_b: str, config_path: str, output: str):
    """Internal async runner for the diff command."""
    try:
        config = load_config(config_path)
        
        # 1. Decompile
        decompiler = Decompiler(config.ghidra)
        
        console.print("[bold blue]Step 1/5:[/bold blue] Decompiling binaries...")
        funcs_a = decompiler.decompile(Path(file_a))
        funcs_b = decompiler.decompile(Path(file_b))
        
        # 2. Match & Diff
        console.print("[bold blue]Step 2/5:[/bold blue] Matching functions and computing diff...")
        engine = DiffEngine(config.diff.function_match_threshold)
        diffs = engine.compute_diff(funcs_a, funcs_b)
        
        modified = [d for d in diffs if d.status == "modified"]
        console.print(f"  Found {len(modified)} modified functions.")
        
        if not modified:
            console.print("[yellow]No modified functions to analyze.[/yellow]")
            return

        # 3. Analyze & Review
        console.print(f"[bold blue]Step 3/5:[/bold blue] Analyzing and reviewing {len(modified)} changes...")
        
        analyzer_llm = LLMClient(config.agents["analyzer"])
        critic_llm = LLMClient(config.agents.get("critic", config.agents["analyzer"]))
        clusterer_llm = LLMClient(config.agents.get("clusterer", config.agents["analyzer"]))
        
        analyzer = FunctionAnalyzer(analyzer_llm)
        critic = ChangeCritic(critic_llm)
        clusterer = ChangeClusterer(clusterer_llm)
        
        semaphore = asyncio.Semaphore(config.diff.max_parallel_analyses)
        
        async def analyze_and_review(d):
            async with semaphore:
                # Initial analysis
                res = await analyzer.analyze(
                    d.name, 
                    d.func_a.decompiled, 
                    d.func_b.decompiled
                )
                
                # Peer review
                review = await critic.review(
                    d.name,
                    d.func_a.decompiled,
                    d.func_b.decompiled,
                    res
                )
                
                final_res = review["adjusted_analysis"] if not review["approved"] else res
                final_res["name"] = d.name
                final_res["critic_flags"] = review.get("flags", [])
                return final_res

        tasks = [analyze_and_review(d) for d in modified]
        results = await asyncio.gather(*tasks)
        
        # 4. Cluster
        console.print("[bold blue]Step 4/5:[/bold blue] Clustering changes into themes...")
        clusters = await clusterer.cluster(results)
        
        # 5. Report
        console.print(f"[bold blue]Step 5/5:[/bold blue] Generating report at {output}...")
        render_markdown(results, Path(output), clusters=clusters)
        
        console.print("[bold green]Success![/bold green] Analysis complete.")

    except Exception as e:
        logger.exception(f"Fatal error during analysis: {e}")
        raise click.Abort()


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
    asyncio.run(_run_diff(file_a, file_b, config, output))


if __name__ == "__main__":
    main()
