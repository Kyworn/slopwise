"""Change clustering agent: groups related changes by theme."""

from slopwise.llm import LLMClient


class ChangeClusterer:
    """Group analyzed changes into semantic clusters.

    Uses an LLM to identify themes (e.g., "all crypto updates", "all bounds checks")
    and organize per-function analyses into coherent narrative categories.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize clusterer with LLM backend.

        Args:
            llm_client: Configured LLMClient instance for any provider/model
        """
        self.llm_client = llm_client

    async def cluster(self, analyses: list[dict]) -> dict[str, list[dict]]:
        """Group function analyses by semantic theme.

        Args:
            analyses: List of analysis dicts from FunctionAnalyzer
                     (each has category, summary, risk, etc.)

        Returns:
            Dict mapping theme name -> list of analyses in that cluster
        """
        raise NotImplementedError("ChangeClusterer.cluster() pending LLM integration")
