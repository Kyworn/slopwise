"""Per-function semantic analysis agent."""

from slopwise.llm import LLMClient


class FunctionAnalyzer:
    """Analyze semantic changes in individual functions via LLM.

    Prompts the LLM to classify each change (bugfix, feature, refactor, security)
    and provide a human-readable summary and risk assessment.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize analyzer with LLM backend.

        Args:
            llm_client: Configured LLMClient instance for any provider/model
        """
        self.llm_client = llm_client

    async def analyze(self, func_a_decompile: str, func_b_decompile: str) -> dict:
        """Analyze difference between two function versions.

        Args:
            func_a_decompile: Decompiled pseudocode from version A (or empty if new)
            func_b_decompile: Decompiled pseudocode from version B (or empty if removed)

        Returns:
            Dict with keys:
            - category: str (e.g., "bugfix", "feature", "refactor", "security")
            - summary: str (2-3 sentence explanation of what changed and why)
            - risk: str (e.g., "low", "medium", "high")
        """
        raise NotImplementedError(
            "FunctionAnalyzer.analyze() pending LLM prompt integration"
        )
