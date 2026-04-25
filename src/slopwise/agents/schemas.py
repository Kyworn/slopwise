"""Pydantic schemas for agent inputs and outputs.

Centralizing the enum values here means the analyzer prompt, the critic
prompt, the clusterer prompt, and the report renderer all see the same
canonical strings -- no drift between "Bugfix" and "bugfix", no surprise
"Refactor / logic modification" categories invented at inference time.
"""

from typing import Literal, get_args

from pydantic import BaseModel, Field

Category = Literal["bugfix", "feature", "refactor", "security", "other"]
Risk = Literal["low", "medium", "high"]

CATEGORIES: tuple[str, ...] = get_args(Category)
RISKS: tuple[str, ...] = get_args(Risk)


class AnalysisResult(BaseModel):
    """A single per-function analysis from the analyzer (or adjusted by the
    critic). All free-form fields are kept as strings so the renderer can
    decide formatting; only `category` and `risk` are enum-constrained."""

    model_config = {"extra": "ignore", "str_strip_whitespace": True}

    category: Category
    risk: Risk
    summary: str
    details: str = ""


class CriticResult(BaseModel):
    """Outcome of the critic pass over an `AnalysisResult`. When `approved`
    is true the original analysis stands; otherwise `adjusted_analysis`
    must be supplied. `flags` should only contain concrete, evidence-backed
    notes -- see the critic prompt."""

    model_config = {"extra": "ignore"}

    approved: bool
    flags: list[str] = Field(default_factory=list)
    adjusted_analysis: AnalysisResult | None = None


class ClusterResult(BaseModel):
    """Mapping of theme name -> list of function names. Theme names are
    free-form (the LLM picks them) but each function name in the values
    must appear in at least one theme."""

    model_config = {"extra": "ignore"}

    themes: dict[str, list[str]]
