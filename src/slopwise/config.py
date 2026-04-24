"""Configuration management for slopwise."""

import os
import re
from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for a specific LLM agent."""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class GhidraConfig(BaseModel):
    """Ghidra-specific settings."""
    ghidra_home: Path


class DiffConfig(BaseModel):
    """Analysis and matching settings."""
    function_match_threshold: float = 0.85
    max_parallel_analyses: int = 4


class OutputConfig(BaseModel):
    """Report generation settings."""
    include_unchanged: bool = False
    risk_threshold: str = "medium"


class Config(BaseModel):
    """Root configuration object."""
    ghidra: GhidraConfig
    agents: Dict[str, AgentConfig]
    diff: DiffConfig = Field(default_factory=DiffConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def _expand_env_vars(text: str) -> str:
    """Expand ${VAR} or $VAR environment variables in a string."""
    pattern = re.compile(r"\$(?:\{(\w+)\}|(\w+))")

    def replacer(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, match.group(0))

    return pattern.sub(replacer, text)


def load_config(path: str | Path) -> Config:
    """Load and parse configuration from a YAML file.

    Args:
        path: Path to config.yaml

    Returns:
        Validated Config object
    """
    with open(path, "r") as f:
        # Read file and expand env vars before YAML parsing
        content = _expand_env_vars(f.read())
        data = yaml.safe_load(content)

    return Config(**data)
