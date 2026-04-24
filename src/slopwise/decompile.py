"""Ghidra headless wrapper for binary decompilation."""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .config import GhidraConfig

logger = logging.getLogger(__name__)


class Decompiler:
    """Wrapper for Ghidra Headless decompilation."""

    def __init__(self, config: GhidraConfig):
        """Initialize decompiler with Ghidra settings.

        Args:
            config: GhidraConfig object containing ghidra_home
        """
        self.ghidra_home = Path(config.ghidra_home)
        self.analyze_headless = self.ghidra_home / "support" / "analyzeHeadless"
        
        if not self.analyze_headless.exists():
            raise FileNotFoundError(
                f"Ghidra analyzeHeadless not found at {self.analyze_headless}. "
                "Check ghidra_home in config."
            )

    def decompile(self, binary_path: Path) -> List[Dict[str, Any]]:
        """Decompile a binary and return function data.

        Args:
            binary_path: Path to the binary file to analyze

        Returns:
            List of dicts containing 'name', 'signature', 'decompiled', 'address'
        """
        binary_path = Path(binary_path).absolute()
        script_path = Path(__file__).parent.parent.parent / "ghidra_scripts"
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            project_name = "slopwise_proj"
            
            cmd = [
                str(self.analyze_headless),
                str(tmp_path),
                project_name,
                "-import", str(binary_path),
                "-postScript", "decompile_all.py",
                "-scriptPath", str(script_path),
                "-deleteProject",
                "-noanalysis" # We just want decompilation for now
            ]
            
            logger.info(f"Running Ghidra analysis on {binary_path}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> List[Dict[str, Any]]:
        """Extract JSON data from Ghidra stdout."""
        start_marker = "---SLOPWISE-START---"
        end_marker = "---SLOPWISE-END---"
        
        if start_marker not in stdout or end_marker not in stdout:
            logger.error("Ghidra script markers not found in output")
            logger.debug(f"Full stdout: {stdout}")
            return []
            
        try:
            json_str = stdout.split(start_marker)[1].split(end_marker)[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse Ghidra output: {e}")
            return []
