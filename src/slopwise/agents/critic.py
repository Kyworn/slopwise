"""Review agent: double-checks dubious claims in analyses."""

from slopwise.llm import LLMClient


class ChangeCritic:
    """Review and validate analyses for consistency and accuracy.

    A second LLM pass to flag contradictions, overstated claims, or missed context.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize critic with LLM backend.

        Args:
            llm_client: Configured LLMClient instance for any provider/model
        """
        self.llm_client = llm_client

    async def review(self, analysis: dict, context: dict) -> dict:
        """Review an analysis for validity and coherence.

        Args:
            analysis: Analysis dict from FunctionAnalyzer (category, summary, risk)
            context: Additional context (e.g., surrounding function names, syscall names)

        Returns:
            Dict with keys:
            - approved: bool
            - flags: list[str] (any concerns raised)
            - adjusted_summary: str (refined explanation if issues found)
        """
        raise NotImplementedError("ChangeCritic.review() pending LLM integration")
