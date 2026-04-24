"""Report generation and formatting."""

from pathlib import Path
from typing import Any, Dict, List


def render_markdown(
    results: List[Dict[str, Any]], 
    output_path: Path,
    clusters: Dict[str, List[str]] = None
) -> None:
    """Render analyzed changes to markdown report.

    Args:
        results: List of dicts with analysis results
        output_path: Path to write report.md
        clusters: Mapping of theme -> list of function names
    """
    with open(output_path, "w") as f:
        f.write("# Slopwise Semantic Diff Report\n\n")
        
        # Summary statistics
        categories = {}
        risks = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        res_map = {r["name"]: r for r in results}
        
        for res in results:
            cat = res.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1
            risk = res.get("risk", "unknown").lower()
            risks[risk] = risks.get(risk, 0) + 1
            
        f.write("## Executive Summary\n\n")
        
        # New: Summary by Themes
        if clusters:
            f.write("### Themes Found\n\n")
            for theme, funcs in clusters.items():
                f.write(f"- **{theme}**: {len(funcs)} functions affected.\n")
            f.write("\n")

        f.write("| Category | Count |\n")
        f.write("| :--- | :--- |\n")
        for cat, count in sorted(categories.items()):
            f.write(f"| {cat.capitalize()} | {count} |\n")
        f.write("\n")
        
        f.write("| Risk Level | Count |\n")
        f.write("| :--- | :--- |\n")
        for risk, count in risks.items():
            if count > 0:
                f.write(f"| {risk.capitalize()} | {count} |\n")
        f.write("\n")
        
        f.write("## Detailed Analysis\n\n")
        
        if clusters:
            # Display by clusters
            for theme, func_names in clusters.items():
                f.write(f"### Theme: {theme}\n\n")
                for name in func_names:
                    if name in res_map:
                        _write_function_entry(f, res_map[name])
        else:
            # Fallback to category grouping
            for cat in sorted(categories.keys()):
                f.write(f"### Category: {cat.capitalize()}\n\n")
                cat_results = [r for r in results if r.get("category") == cat]
                for res in cat_results:
                    _write_function_entry(f, res)

def _write_function_entry(f, res):
    """Helper to write a single function entry in the report."""
    f.write(f"#### `{res['name']}`\n\n")
    f.write(f"- **Risk**: {res.get('risk', 'unknown').upper()}\n")
    f.write(f"- **Category**: {res.get('category', 'unknown').capitalize()}\n")
    f.write(f"- **Summary**: {res.get('summary', 'N/A')}\n")
    
    if res.get("critic_flags"):
        f.write(f"- **Reviewer Notes**: {', '.join(res['critic_flags'])}\n")
        
    if res.get("details"):
        f.write(f"\n**Technical Details**:\n{res['details']}\n")
    
    f.write("\n---\n\n")
