"""Firmware unpacking and extraction utilities."""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class Unpacker:
    """Handles firmware extraction (SquashFS, OTA payloads, etc.)."""

    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="slopwise_unpack_"))

    def unpack(self, file_path: Path) -> List[Path]:
        """Extract a firmware image and return list of discovered binaries.

        Args:
            file_path: Path to the firmware/container file

        Returns:
            List of absolute paths to extracted files
        """
        file_path = Path(file_path).absolute()
        extract_dir = self.work_dir / file_path.name
        extract_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Attempting to unpack {file_path}...")

        # Try binwalk if available
        if shutil.which("binwalk"):
            try:
                subprocess.run(
                    ["binwalk", "-e", "-M", "-C", str(extract_dir), str(file_path)],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                logger.warning(f"Binwalk failed: {e.stderr}")

        # Fallback/specific support: squashfs
        if shutil.which("unsquashfs"):
            try:
                subprocess.run(
                    ["unsquashfs", "-d", str(extract_dir / "squashfs-root"), str(file_path)],
                    capture_output=True
                )
            except Exception:
                pass

        # Return all files found in the extraction directory
        return [f for f in extract_dir.rglob("*") if f.is_file()]

    def cleanup(self):
        """Remove temporary extraction directory."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
