"""Function matching and diffing."""

from typing import Literal


class FunctionMatcher:
    """Match and diff functions across binary versions."""

    def match(
        self, a_funcs: dict[str, str], b_funcs: dict[str, str]
    ) -> list[tuple[str, str, Literal["added", "removed", "modified"]]]:
        """Match functions between two binaries and classify changes.

        Args:
            a_funcs: Function name/addr -> decompiled source from version A
            b_funcs: Function name/addr -> decompiled source from version B

        Returns:
            List of (func_name_a, func_name_b, status) tuples where status is:
            - "added": function exists only in B
            - "removed": function exists only in A
            - "modified": function exists in both but differs
        """
        raise NotImplementedError(
            "FunctionMatcher.match() pending fuzzy matching implementation"
        )
