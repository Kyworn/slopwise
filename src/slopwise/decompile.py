"""Ghidra integration for binary decompilation."""

from pathlib import Path


class GhidraDecompiler:
    """Decompile binaries to function source via Ghidra headless."""

    def __init__(self, ghidra_home: Path):
        """Initialize Ghidra decompiler.

        Args:
            ghidra_home: Path to Ghidra installation directory
        """
        self.ghidra_home = Path(ghidra_home)

    def decompile_functions(self, binary_path: Path) -> dict[str, str]:
        """Decompile all functions in a binary to pseudocode.

        Args:
            binary_path: Path to ELF/Mach-O/PE binary

        Returns:
            Dict mapping function name/address -> decompiled pseudocode string
        """
        raise NotImplementedError(
            "GhidraDecompiler.decompile_functions() pending Ghidra integration"
        )
