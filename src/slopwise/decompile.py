"""Ghidra headless wrapper for binary decompilation, with content-addressed cache."""

import hashlib
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import GhidraConfig

logger = logging.getLogger(__name__)


def _cache_root() -> Path:
    """Cache lives under XDG_CACHE_HOME (or ~/.cache) by convention."""
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "slopwise" / "decomp"


class Decompiler:
    """Wrapper for Ghidra Headless decompilation.

    Results are cached under `~/.cache/slopwise/decomp/<sha256>.json`.
    The cache key hashes the binary bytes together with the Ghidra script
    bytes, so changes to either invalidate the cached output. Pass
    `use_cache=False` to bypass.
    """

    SCRIPT_NAME = "decompile_all.java"

    def __init__(self, config: GhidraConfig, use_cache: bool = True):
        self.ghidra_home = Path(config.ghidra_home)
        self.analyze_headless = self.ghidra_home / "support" / "analyzeHeadless"
        self.use_cache = use_cache

        if not self.analyze_headless.exists():
            raise FileNotFoundError(
                f"Ghidra analyzeHeadless not found at {self.analyze_headless}. "
                "Check ghidra_home in config."
            )

    @property
    def script_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "ghidra_scripts"

    @property
    def script_path(self) -> Path:
        return self.script_dir / self.SCRIPT_NAME

    def cache_key(self, binary_path: Path) -> str:
        """SHA-256 of (binary bytes, ghidra script bytes). Stable across
        runs; changes whenever either input changes."""
        h = hashlib.sha256()
        h.update(binary_path.read_bytes())
        if self.script_path.exists():
            h.update(self.script_path.read_bytes())
        return h.hexdigest()

    def _cache_path(self, key: str) -> Path:
        return _cache_root() / f"{key}.json"

    def _try_cache_load(self, key: str) -> Optional[List[Dict[str, Any]]]:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Ignoring corrupt decomp cache %s: %s", path, e)
            return None

    def _cache_store(self, key: str, data: List[Dict[str, Any]]) -> None:
        path = self._cache_path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            with open(tmp, "w") as f:
                json.dump(data, f)
            tmp.replace(path)
        except OSError as e:
            logger.warning("Failed to write decomp cache %s: %s", path, e)

    def decompile(self, binary_path: Path) -> List[Dict[str, Any]]:
        binary_path = Path(binary_path).absolute()

        if self.use_cache:
            key = self.cache_key(binary_path)
            cached = self._try_cache_load(key)
            if cached is not None:
                logger.info("Decomp cache hit for %s (%s)", binary_path.name, key[:12])
                return cached
        else:
            key = ""

        data = self._run_ghidra(binary_path)

        if self.use_cache and key and data:
            self._cache_store(key, data)

        return data

    def _run_ghidra(self, binary_path: Path) -> List[Dict[str, Any]]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            project_name = "slopwise_proj"
            out_json = tmp_path / "output.json"

            cmd = [
                str(self.analyze_headless),
                str(tmp_path),
                project_name,
                "-import", str(binary_path),
                "-postScript", self.SCRIPT_NAME,
                str(out_json),
                "-scriptPath", str(self.script_dir),
                "-deleteProject",
                "-noanalysis",
            ]

            logger.info("Running Ghidra analysis on %s...", binary_path)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if not out_json.exists():
                logger.error("Ghidra analysis failed, output JSON not created.")
                logger.debug("Ghidra stderr/stdout: %s\n%s", result.stdout, result.stderr)
                return []

            try:
                with open(out_json, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON from Ghidra: %s", e)
                return []
